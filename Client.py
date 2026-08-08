import socket
import threading

# Change this to the server computer's IPv4 address
# when the client is running on a different computer.
SERVER_IP = "127.0.0.1"

# Must match the SERVER_PORT in server.py
SERVER_PORT = 4270

client_running = True


def receive_messages(client_socket):
    """
    Continuously receive messages from the server.

    This runs in its own thread so messages from another client can
    appear even while this client is waiting for keyboard input.
    """
    global client_running

    receive_buffer = ""
    list_mode = False

    try:
        while client_running:
            data = client_socket.recv(4096)

            if not data:
                if client_running:
                    print("\nConnection to server closed.")
                client_running = False
                break

            receive_buffer += data.decode("utf-8")

            while "\n" in receive_buffer:
                message, receive_buffer = receive_buffer.split("\n", 1)

                if message == "END_LIST":
                    list_mode = False
                    continue

                if message == "SERVER_SHUTDOWN":
                    print("\nS: Server is shutting down.")
                    client_running = False
                    return

                # LIST results are sent as several lines.
                if list_mode:
                    print(message)
                    continue

                if (
                    message in ("root", "john", "sally", "qiang")
                    or message.startswith("    ")
                ):
                    # Start displaying multiline LIST output.
                    list_mode = True
                    print(f"\nS: {message}")
                    continue

                print(f"\nS: {message}")

                # The server confirms LOGOUT/SHUTDOWN with 200 OK.
                # The main input loop decides whether it should exit
                # based on the command that was just sent.

    except (ConnectionResetError, ConnectionAbortedError, OSError):
        if client_running:
            print("\nLost connection to server.")

        client_running = False


def main():
    global client_running

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((SERVER_IP, SERVER_PORT))
    except ConnectionRefusedError:
        print("Could not connect to the server.")
        print("Make sure server.py is running and SERVER_IP is correct.")
        return
    except OSError as error:
        print(f"Connection error: {error}")
        return

    print("Connected to MatheMagic Online.")
    print(f"Server: {SERVER_IP}:{SERVER_PORT}")
    print()
    print("Commands:")
    print("  LOGIN username password")
    print("  SOLVE -c radius")
    print("  SOLVE -r side")
    print("  SOLVE -r side1 side2")
    print("  LIST")
    print("  LIST -all")
    print("  MESSAGE username message")
    print("  MESSAGE -all message")
    print("  LOGOUT")
    print("  SHUTDOWN")
    print()

    receiver_thread = threading.Thread(
        target=receive_messages,
        args=(client_socket,),
        daemon=True
    )
    receiver_thread.start()

    try:
        while client_running:
            try:
                command = input("C: ").strip()
            except EOFError:
                break

            if not command:
                continue

            try:
                client_socket.sendall((command + "\n").encode("utf-8"))
            except OSError:
                print("Unable to send command. Connection was closed.")
                break

            command_name = command.split()[0].upper()

            # The assignment says LOGOUT terminates only the client
            # after it receives the confirmation from the server.
            if command_name in ("LOGOUT", "SHUTDOWN"):
                receiver_thread.join(timeout=1.5)

                if command_name == "LOGOUT":
                    client_running = False
                    break

                if command_name == "SHUTDOWN":
                    client_running = False
                    break

    except KeyboardInterrupt:
        print("\nClient closed.")

    finally:
        client_running = False

        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        try:
            client_socket.close()
        except OSError:
            pass

        print("Client terminated.")


if __name__ == "__main__":
    main()