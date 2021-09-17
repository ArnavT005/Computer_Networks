import sys
import socket
import threading


def parse_command_line():
    
    # check if sufficient command line arguments are provided, or not
    if len(sys.argv) < 3:
        print("Error: Insufficient number of command line arguments. Program terminating!")
        return None
    elif len(sys.argv) > 3:
        print("Warning: Extra command line arguments provided. Only three arguments are expected!")
    
    # parse arguments and return username and IP address of the server
    username = sys.argv[1]
    server_addr = sys.argv[2]
    return username, server_addr

def parse_data(data, delim=' '):
    fields = []
    temp = ""
    for i in range(0, len(data)):
        if data[i] == delim:
            fields.append(temp)
            temp = ""
        else:
            temp = temp + data[i]
    if temp != "":
        fields.append(temp)
    return fields

def send_message(sock_send):
    
    # print welcome message
    print("Welcome to Datagram!")
    print("Enter your chat messages below. Use \"@[user]\" to ping a particular member or \"@ALL\" to broadcast message to all members.")

    # loop forever
    while True:
        # user prompt
        chat_message = input()
        # check if message is valid
        if chat_message == "" or chat_message[0] != "@":
            # incorrect message format
            print("Warning: Incorrect format. Use \"@[user]\" to ping a particular member or \"@ALL\" to broadcast message to all members.")
            continue
        
        # valid message, parse data to get recipient name and message
        recp_name = ""
        message = ""
        switch = False
        for i in range(1, len(chat_message)):
            if switch:
                message = message + chat_message[i]
            elif chat_message[i] == " ":
                switch = True
            else:
                recp_name = recp_name + chat_message[i]
        
        # check if any field is empty
        if recp_name == "":
            print("Warning: No username specified. Please try again.")
            continue

        # check if message is empty
        if message == "":
            print("Warning: Empty message. Please try again.")
            continue

        # send message to server
        content_length = len(message.encode())
        send_message = "SEND " + recp_name + "\nContent-length: " + str(content_length) + "\n\n" + message
        try:
            sock_send.sendall(send_message.encode())
        except:
            # some error, close thread
            print("Network Error: Unable to send message. Please try again.")
            return

        # wait for reply from server
        try:
            ack_message = sock_send.recv(2048)
        except:
            # some error, close thread
            print("Network Error: Unable to send message. Please try again.")
            return
        
        # check response
        if ack_message.decode() == "ERROR 102 Unable to send\n\n":
            # server was unable to find recipient
            print("FAILURE: Server was unable to find the recipient. Verify recipient name and please try again.")
        elif ack_message.decode() == "ERROR 103 Header Incomplete\n\n":
            # header was not fully specified
            print("FAILURE: Header information incomplete. Closing connection!")
            return
        elif ack_message.decode() == "ERROR 105 Broadcasting Error\n\n":
            # server was unable to broadcast message to all
            print("FAILURE: Server was unable to send message to all. Please try again.")
        elif ack_message.decode() == "SENT " + recp_name + "\n\n":
            print("SUCCESS: Message delivered to " + recp_name + " successfully!")
        else:
            # some unexpected error (ERROR 104)
            print("Error: Unexpected response from user. Please try again.")

def recv_message(sock_recv):

    while True:
        # wait for messages from server
        try:
            incoming_message = sock_recv.recv(2048)
        except:
            # some error, close thread
            return
        
        fields = parse_data(incoming_message.decode(), '\n')
        
        # check if header is complete
        if len(fields) < 4 or len(fields) > 4 or fields[2] != "":
            # error in packet
            try:
                sock_recv.sendall(("ERROR 103 Header Incomplete\n\n").encode())
            except:
                # some error, close thread
                return
            continue

        # parse all header lines of message   
        first_line = parse_data(fields[0])
        second_line = parse_data(fields[1])
        # store user message
        user_message = fields[3]
        
        # set error flag
        error = False

        # check first line
        if len(first_line) < 2 or len(first_line) > 2:
            error = True
        else:
            if first_line[0] != "FORWARD":
                error = True
            else:
                sender_name = first_line[1]

        # check second line
        if len(second_line) < 2 or len(second_line) > 2:
            error = True
        else:
            if second_line[0] != "Content-length:" or not second_line[1].isdigit():
                error = True
            else:
                content_length = int(second_line[1])
                # check if the content length is correct or not
                if len(user_message.encode()) != content_length:
                    error = True

        # check for error
        if error:
            # send message to server
            try:
                sock_recv.sendall(("ERROR 103 Header Incomplete\n\n").encode())
            except:
                # some error, close thread
                return
            continue
        
        # no errors, send "received" message to server, and display message
        print("MESSAGE from " + sender_name + ": " + user_message)
        try:
            sock_recv.sendall(("RECEIVED " + sender_name + "\n\n").encode())
        except:
            # some error, close thread
            return
        
def main():
    
    # parse command line arguments, exit on error
    try:
        username, server_addr = parse_command_line()
    except:
        # return on error
        return
    
    # establish TCP connection (on port 8000) with server for sending messages, return on error
    try:
        sock_send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_send.connect((server_addr, 8000))
    except:
        print("Error: Unable to establish connection with the server. Ensure that the IP address provided is correct and try again.")
        return

    # connection established, register user
    try:
        sock_send.sendall(("REGISTER TOSEND " + username + "\n\n").encode())
    except:
        # some error
        print("Network Error: Please try again later.")
        sock_send.close()
        return
    
    # wait for acknowledgment from server
    try:
        ack_message = sock_send.recv(2048)
    except:
        # some error
        print("Network Error: Please try again later.")
        sock_send.close()
        return
    
    # check for errors
    if ack_message.decode() == "ERROR 100 Malformed username\n\n":
        # username is not valid
        print("Name Error: Illegal username provided. Only alphanumeric characters are allowed! (NO SPACES)")
        sock_send.close()
        return
    elif ack_message.decode() == "ERROR 101 No user registered\n\n":
        # registration was unsuccessful
        print("Server Error: You need to be registered before sending any other messages. Please try again.")
        sock_send.close()
        return
    elif ack_message.decode() != "REGISTERED TOSEND " + username + "\n\n":
        # unexpected response, close connection
        print("Error: Unexpected response from user. Please try again.")
        sock_send.close()
        return
    
    # registration successful (for sending)

    # establish TCP connection (on port 8000) with server for receiving messages, return on error
    try:
        sock_recv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_recv.connect((server_addr, 8000))
    except:
        print("Error: Unable to establish connection with the server. Ensure that the IP address provided is correct and try again.")
        sock_send.close()
        return

    # connection established, register user
    try:
        sock_recv.sendall(("REGISTER TORECV " + username + "\n\n").encode())
    except:
        # some error
        print("Network Error: Please try again later.")
        sock_send.close()
        sock_recv.close()
        return

    # wait for acknowledgment from server
    try:
        ack_message = sock_recv.recv(2048)
    except:
        # some error
        print("Network Error: Please try again later.")
        sock_send.close()
        sock_recv.close()
        return

    # check for errors    
    if ack_message.decode() == "ERROR 100 Malformed username\n\n":
        # username is not valid
        print("Name Error: Illegal username provided. Only alphanumeric characters are allowed! (NO SPACES)")
        sock_send.close()
        sock_recv.close()
        return
    elif ack_message.decode() == "ERROR 101 No user registered\n\n":
        # registration was unsuccessful
        print("Server Error: You need to be registered before sending any other messages. Please try again.")
        sock_send.close()
        sock_recv.close()
        return
    elif ack_message.decode() != "REGISTERED TORECV " + username + "\n\n":
        # unexpected response, close connection
        print("Error: Unexpected response from user. Please try again.")
        sock_send.close()
        sock_recv.close()
        return
    
    # registration successful (for receiving)

    # user registration successful
    print("User registration successful. Chatting enabled!")

    # create threads for client-side sending and receiving respectively
    try:
        thread_send = threading.Thread(target=send_message, args=(sock_send,))
        thread_recv = threading.Thread(target=recv_message, args=(sock_recv,))
    except:
        print("Thread Error: There was an issue with multi-threading. Please try again later.")
        sock_send.close()
        sock_recv.close()
        return

    # start threads
    thread_send.start()
    thread_recv.start()

    # wait for threads to finish
    thread_send.join()
    thread_recv.join()

    # close sockets
    sock_send.close()
    sock_recv.close()

    print("\nConnection closed. If this was unexpected, then there may have been some error. Please try again in that case.")


# run driver
main()
