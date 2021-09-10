import sys
import socket
import threading


def parse_command_line():
    
    # check if sufficient command line arguments are provided, or not
    if len(sys.argv) < 3:
        print("Error: Insufficient number of command line arguments. Program terminating!")
        return False, "", ""
    elif len(sys.argv) > 3:
        print("Warning: Extra command line arguments provided. Only three arguments are needed!")
    
    # parse arguments and return username and IP address of the server
    username = sys.argv[1]
    server_IP = sys.argv[2]
    return True, username, server_IP

def close_connection(sock1=None, sock2=None):
    
    # close TCP connections
    if sock1 != None:
        sock1.close()
    if sock2 != None:
        sock2.close()

def parse_data(data, delim=' '):
    fields = []
    temp = ""
    for i in range(0, len(data)):
        if data[i] == delim:
            if temp != "":
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
    print("Enter your message after \">\" icon. Use \"@[user]\" to ping a particular member or \"@ALL\" to broadcast message to all members.")

    # loop forever
    while True:
        # user prompt
        chat_message = input("> ")
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
        
        # send message to server
        content_length = len(message.encode())
        send_message = "SEND " + recp_name + "\nContent-length: " + str(content_length) + "\n\n" + message
        try:
            sock_send.send(send_message.encode())
        except:
            # some error, close thread
            return

        # receive reply (unicast)
        if recp_name != "ALL":
            # wait for reply from server
            try:
                ack_message = sock_send.recv(4096)
            except:
                # some error, close thread
                return
            # decode reply
            if ack_message.decode() == "SENT " + recp_name + "\n\n":
                print("SUCCESS: Message delivered to " + recp_name + " successfully!")
            elif ack_message.decode() == "ERROR 102 Unable to send\n\n":
                # server was unable to find recipient
                print("FAILURE: Server was unable to find the recipient. Verify recipient name and please try again.")
            elif ack_message.decode() == "ERROR 103 Header Incomplete\n\n":
                # header was not fully specified
                print("FAILURE: Header information incomplete. Closing connection!")
                return
            else:
                # some unexpected error
                print("Error: Unexpected response from server. Please try again.")
            continue
        
        # else, receive reply (broadcast)
        while True:
            # wait for reply from server
            try:
                ack_message = sock_send.recv(4096)
            except:
                # some error, close thread
                return
            # parse reply
            fields = parse_data(ack_message.decode(), delim='\n')
            # check response
            if len(fields) > 1 or len(fields) < 1:
                # unexpected reply from server
                print("Error: Unexpected response from server. Please try again.")
                continue
            # parse first line
            fields = parse_data(fields[0])
            if len(fields) == 2 and fields[0] == "SENT":
                print("SUCCESS: Message delivered to " + fields[1] + " successfully!")
            elif ack_message.decode() == "ERROR 102 Unable to send\n\n":
                # server was unable to find recipient
                print("FAILURE: Server was unable to find the recipient. Verify recipient name and please try again.")
            elif ack_message.decode() == "ERROR 103 Header Incomplete\n\n":
                # header was not fully specified
                print("FAILURE: Header information incomplete. Closing connection!")
                return
            elif ack_message.decode() == "ALL DONE\n\n":
                # all replies received, break
                break
            else:
                # some unexpected error
                print("Error: Unexpected response from server. Please try again.")

    return

def recv_message(sock_recv):

    while True:
        # wait for messages from server
        try:
            incoming_message = sock_recv.recv(4096)
        except:
            # some error, close thread
            return
        fields = parse_data(incoming_message.decode(), '\n')
        
        # check if header is complete
        if len(fields) < 3 or len(fields) > 3:
            # error in packet
            try:
                sock_recv.send(("ERROR 103 Header Incomplete\n\n").encode())
            except:
                # some error, close thread
                return
            continue

        # parse all header lines of message   
        first_line = parse_data(fields[0])
        second_line = parse_data(fields[1])
        # store user message
        user_message = fields[2]
        
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
                sock_recv.send(("ERROR 103 Header Incomplete\n\n").encode())
            except:
                # some error, close thread
                return
            continue
        
        # no errors, send "received" message to server, and display message
        print("MESSAGE from " + sender_name + ": " + user_message)
        try:
            sock_recv.send(("RECEIVED " + sender_name + "\n\n").encode())
        except:
            # some error, close thread
            return
        
def main():
    
    # parse command line arguments, exit on error
    flag, username, server_IP = parse_command_line()
    # check for error
    if not flag:
        sys.exit()
    
    # establish TCP connection (on port 8000) with server for sending messages, exit on error
    try:
        sock_send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_send.connect((server_IP, 8000))
    except:
        print("Error: Unable to establish connection with the server. Ensure that the IP address provided is correct and try again later.")
        sys.exit()

    # connection established, register user
    try:
        sock_send.send(("REGISTER TOSEND " + username + "\n\n").encode())
    except:
        # some error
        print("Network Error: Please try again later.")
        return
    # wait for acknowledgment from server
    try:
        ack_message = sock_send.recv(4096)
    except:
        # some error
        print("Network Error: Please try again later.")
        return
    if ack_message.decode() == "ERROR 100 Malformed username\n\n":
        # username is not valid
        print("Error: Illegal username provided. Only alphanumeric characters are allowed! (NO SPACES)")
        close_connection(sock_send)
        sys.exit()
    elif ack_message.decode() != "REGISTERED TOSEND " + username + "\n\n":
        # registration was unsuccessful
        print("Error: Registration was unsuccessful. Please try again later.")
        close_connection(sock_send)
        sys.exit()
    # registration successful (for sending)

    # establish TCP connection (on port 8000) with server for receiving messages, exit on error
    try:
        sock_recv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_recv.connect((server_IP, 8000))
    except:
        print("Error: Unable to establish connection with the server. Ensure that the IP address provided is correct and try again later.")
        sys.exit()

    # connection established, register user
    try:
        sock_recv.send(("REGISTER TORECV " + username + "\n\n").encode())
    except:
        # some error
        print("Network Error: Please try again later.")
        return
    # wait for acknowledgment from server
    try:
        ack_message = sock_recv.recv(4096)
    except:
        # some error
        print("Network Error: Please try again later.")
        return
    if ack_message.decode() == "ERROR 100 Malformed username\n\n":
        # username is not valid
        print("Error: Illegal username provided. Only alphanumeric characters are allowed! (NO SPACES)")
        close_connection(sock_send, sock_recv)
        sys.exit()
    elif ack_message.decode() != "REGISTERED TORECV " + username + "\n\n":
        # registration was unsuccessful
        print("Error: Registration was unsuccessful. Please try again later.")
        close_connection(sock_send, sock_recv)
        sys.exit()
    # registration successful (for receiving)

    # user registration successful
    print("User registration successful. Chatting enabled!")

    # create threads for client-side sending and receiving respectively
    try:
        thread_send = threading.Thread(target=send_message, args=(sock_send,))
        thread_recv = threading.Thread(target=recv_message, args=(sock_recv,))
    except:
        print("Error: There was an issue with multi-threading. Please try again later.")
        close_connection(sock_send, sock_recv)
        sys.exit()

    # start threads
    thread_send.start()
    thread_recv.start()


main()
