import subprocess
import time
import speech_recognition as sr
from word2number import w2n
from env import COMMAND_LOCAL_PATH,INSTANCE_TYPE
# Initialize recognizer and other variables
recognizer = sr.Recognizer()
process = None
command_mode = None  # Keeps track of the current mode
expected_input_type = None  # Type of input expected for each prompt

# Define prompt-to-mode mappings
prompts_and_modes = {
    "class name of the entity": ("class_name", "string"),
    "new property name": ("new_property", "string"),
    "field type": ("field_type", "choice"),  # expects "integer", "string", etc.
    "field length": ("field_length", "number"),
    "can this field be null": ("yesnofield", "yesno"),
    "add the ability to broadcast entity" :  ("yesnofield","yesno")
}

def to_camel_case(text):
    # Split the text by spaces, capitalize each word, and join them together
    words = text.strip().split()
    return ''.join(word.capitalize() for word in words)


# Function to capture and recognize voice command
# def recognize_voice_command():
#     with sr.Microphone() as source:
#         print("Listening for command...")
#         audio_data = recognizer.listen(source)
#         try:
#             command = recognizer.recognize_google(audio_data)
#             print(f"Recognized command: {command}")
#             return command.lower()
#         except sr.UnknownValueError:
#             print("Could not understand the audio")
#             return None
#         except sr.RequestError:
#             print("Could not request results from Google Speech Recognition")
#             return None
        
# def recognize_voice_command():
#     with sr.Microphone() as source:
#         recognizer.pause_threshold = 0.5
#         recognizer.energy_threshold = 300

#         print("Listening for command...")
#         audio_data = recognizer.listen(source)

#         try:
#             command = recognizer.recognize_google(audio_data)
#             print(f"Raw Recognized Command: {command}")  # Debugging print

#             # Normalize input for "yes" and "no" variants
#             if command.lower() in ["yes", "yeah", "yep"]:
#                 command = "yes"
#             elif command.lower() in ["no", "nope", "nah"]:
#                 command = "no"

#             print(f"Interpreted Command for yes/no: {command}")
#             return command.lower()
#         except sr.UnknownValueError:
#             print("Could not understand the audio")
#             return None
#         except sr.RequestError:
#             print("Could not request results from Google Speech Recognition")
#             return None

def recognize_voice_command(retries=3):
    attempt = 0
    while attempt < retries:
        with sr.Microphone() as source:
            recognizer.pause_threshold = 0.5
            recognizer.energy_threshold = 300

            print("Listening for command... (Attempt {}/{})".format(attempt + 1, retries))
            audio_data = recognizer.listen(source)

            try:
                # Use Google's speech recognition to transcribe
                command = recognizer.recognize_google(audio_data)
                print(f"Raw Recognized Command: {command}")

                # Normalize for "yes" and "no" variants
                if command.lower() in ["yes", "yeah", "yep", "affirmative"]:
                    command = "yes"
                elif command.lower() in ["no", "nope", "nah", "negative"]:
                    command = "no"

                print(f"Interpreted Command: {command}")
                return command.lower()

            except sr.UnknownValueError:
                print("Could not understand the audio. Retrying...")
                attempt += 1
            except sr.RequestError:
                print("Could not request results from Google Speech Recognition")
                return None

    print("Failed to recognize command after multiple attempts.")
    return None

# Function to handle input based on command mode
def handle_voice_input(command):
    global process, command_mode

    if command_mode == "class_name":
        camel_case_name = to_camel_case(command)
        process.stdin.write(camel_case_name + "\n")
        process.stdin.flush()
        print("Entered Class Name:", camel_case_name)
        command_mode = None  # Reset after use

    elif command_mode == "new_property":
        process.stdin.write(command + "\n")
        process.stdin.flush()
        print("Entered New Property:", command)
        command_mode = None

    elif command_mode == "field_type":
        if command in ["string", "integer"]:  # Expected choices
            process.stdin.write(command + "\n")
            process.stdin.flush()
            print("Entered Field Type:", command)
            command_mode = None

    elif command_mode == "field_length":
        number_command = str(w2n.word_to_num(command))
        # if number_command.isdigit():
        process.stdin.write(number_command + "\n")
        process.stdin.flush()
        print("Entered Field Length:", number_command)
        command_mode = None

    elif command_mode == "yesnofield":
        print("command inside yesnofield is:",command)
        if command in ["yes", "no"]:
            print("yes or no received")
            process.stdin.write(command + "\n")
            process.stdin.flush()
            print("Entered yesnofield:", command)
            command_mode = None
    #     elif command in ["negative"]:
    #         print("negative received")
    #         process.stdin.write("no" + "\n")
    #         process.stdin.flush()
    #         print("Entered yesnofield:", command)
    #         command_mode = None
    #     elif command in ["affirmative"]:
    #         print("affirmative received")
    #         process.stdin.write("yes" + "\n")
    #         process.stdin.flush()
    #         print("Entered yesnofield:", command)
    #         command_mode = None

    # elif command_mode == "yesnofield":
    #     attempts = 0
    #     command = None
    #     while not command and attempts < 3:  # Try up to 3 times
    #         command = recognize_voice_command(1)
    #         attempts += 1
    #         if command in ["yes", "no"]:
    #             process.stdin.write(command + "\n")
    #             process.stdin.flush()
    #             print("Entered Yes/No:", command)
    #             command_mode = None
    #             break
    #         else:
    #             print("Retrying to capture 'yes' or 'no'...")
# Function to run the Symfony command
def run_symfony_command():
    global process, command_mode

    print("Starting Symfony make:entity command in WSL...")
    process = subprocess.Popen(
        [INSTANCE_TYPE, "php", COMMAND_LOCAL_PATH, "make:entity"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Read and interpret each line of output
    while process.poll() is None:
        output_line = process.stdout.readline().strip()
        print(f"Console Output: {output_line}")

        # Check if output matches any known prompts and set command mode
        for prompt, mode in prompts_and_modes.items():
            if prompt in output_line.lower():
                command_mode, expected_input_type = mode
                print(f"Entering mode: {command_mode} (expects {expected_input_type})")
                break  # Stop checking prompts once a match is found

        # Listen and handle voice input based on the active command mode
        if command_mode:
            command = recognize_voice_command(3)
            if command:
                handle_voice_input(command)

    # Final output after process completion
    stdout, stderr = process.communicate()
    print("Command completed.")
    print(f"Final Output:\n{stdout}")
    if stderr:
        print(f"Errors:\n{stderr}")

# Main loop to listen and respond to commands
while True:
    command = recognize_voice_command(3)
    if command == "make entity":
        print("Executing make:entity command...")
        run_symfony_command()
    elif command == "exit":
        print("Exiting voice-controlled shell...")
        break
