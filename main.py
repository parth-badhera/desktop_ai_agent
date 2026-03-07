from parser import execute
import sys
import memory

def main():
    memory.clear_memory()
    print("Local AI Agent Ready")
    print("Type 'exit' or use Ctrl+C to quit.")

    while True:
        try:
            command = input("You: ")

            if command.lower().strip() == "exit":
                print("Goodbye!")
                break
            
            if not command.strip():
                continue

            execute(command)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
