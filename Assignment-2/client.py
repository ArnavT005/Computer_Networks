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

def parse_packet(msg_packet):
    
    # parse the msg_packet received from server
    fields = []
    temp = ""
    for i in range(0, len(msg_packet)):
        if msg_packet[i] == "\n":
            if temp != "":
                fields.append(temp)
                temp = ""
        else:
            temp = temp + msg_packet
    if temp != "":
        fields.append(temp)
    
    # return parsed fields
    return fields

def send_message(sock_send):
    
    print("Welcome to Datagram!")
    print("To quit Datagram, type \"QUIT\" in the prompt below.")
    
    # loop until QUIT
    while True:
        chat_message = input("Enter your message. Use \"@ [user]\" to ping a particular member or \"@ALL\" to broadcast message to all members.")
        if chat_message == "QUIT":
            # quit
            break
        if chat_message == "" or chat_message[0] != "@":
            # incorrect message format
            continue
        
        # valid message, parse recipient name and message
        recp_name = ""
        message = ""
        flag = False
        for i in range(1, len(chat_message)):
            if chat_message[i] == " ":
                flag = True
            elif flag:
                message = message + chat_message[i]
            else:
                recp_name = recp_name + chat_message[i]
        
        # send message to server
        content_length = len(message.decode())
        msg_packet = "SEND " + recp_name + "\nContent-length: " + str(content_length) + "\n\n" + message
        sock_send.send(msg_packet.encode())
        
        # wait for reply from server
        ack_send = sock_send.recv(4096)
        if ack_send.decode() == "SENT " + recp_name + "\n\n":
            print("SRVR: Message delivered to recipient successfully!")
            continue
        elif ack_send.decode() == "ERROR 102 Unable to send\n\n":
            # server was unable to find recipient
            print("RCPT ERROR: Server was unable to find the requested recipient. Verify recipient name and please try again.")
            continue
        elif ack_send.decode() == "ERROR 103 Header incomplete\n\n":
            # header was not fully specified
            print("SRVR Error: Header information incomplete. Closing connection!")
            break
        else:
            # some unexpected error
            print("Error: Unexpected response from server. Closing connection!")
            break
    
    return

def recv_message(sock_recv):

    while True:
        # wait for FORWARDED messages from server
        forwarded_message = sock_recv.recv(4096)
        msg_packet = forwarded_message.decode()

        # parse the packet to extract sender and message
        sendr_name = ""
        message = ""
        fields = parse_packet(msg_packet)
        error = False
        if len(fields) < 3 or len(fields) > 3:
            # error with header
            error = True
        else:
            if len(fields[0]) < 8 or fields[0][0:8] != "FORWARD ":
                # error with header
                error = True
            else:
                sendr_name = fields[0][8:]
                if sendr_name == "":
                    # error with header
                    error = True
            if len(fields[1]) < 16 or fields[1][0:16] != "Content-length: ":
                # error with header
                error = True
            else:
                temp = fields[1][16:]
                if temp == "" or not temp.isdigit():
                    # error with header
                    error = True
                else:
                    content_length = int(temp)
            message = fields[2]
        
        # check for errors
        if error:
            # send message to server
            error_msg = "ERROR 103 Header Incomplete\n\n"
            sock_recv.send(error_msg.encode())
            continue
    
        # no errors, display message to user
        print("MESSAGE from " + sendr_name + ": " + message)

def main():
    
    # parse command line arguments, exit on error
    flag, username, server_IP = parse_command_line()
    if not flag:
        sys.exit()
    
    # establish TCP connection (on port 5000) with server for sending messages, exit on error
    try:
        sock_send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_send.connect((server_IP, 8000))
    except:
        print("Error: Unable to establish connection with the server. Program terminating!")
        sys.exit()
        
    # connection established, register user
    sock_send.send(("REGISTER TOSEND " + username + "\n\n").encode())
    ack_send = sock_send.recv(4096)
    if ack_send.decode() == "ERROR 100 Malformed username\n\n":
        # username is not valid
        print("Error: Illegal username provided. Only alphanumeric characters are allowed! (NO SPACES)")
        close_connection(sock_send)
        sys.exit()
    elif ack_send.decode() != "REGISTERED TOSEND " + username + "\n\n":
        # registration was unsuccessful
        print("Error: Registration was unsuccessful. Please try again later.")
        close_connection(sock_send)
        sys.exit()
    # registration successful (for sending)

    # establish TCP connection (on port 5000) with server for receiving messages, exit on error
    try:
        sock_recv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_recv.connect((server_IP, 5000))
    except:
        print("Error: Unable to establish connection with the server. Program terminating!")
        sys.exit()

    # connection established, register user
    sock_recv.send(("REGISTER TORECV " + username + "\n\n").encode())
    ack_recv = sock_recv.recv(4096)
    if ack_recv.decode() == "ERROR 100 Malformed username\n\n":
        # username is not valid
        print("Error: Illegal username provided. Only alphanumeric characters are allowed! (NO SPACES)")
        close_connection(sock_send, sock_recv)
        sys.exit()
    elif ack_recv.decode() != "REGISTERED TORECV " + username + "\n\n":
        # registration was unsuccessful
        print("Error: Registration was unsuccessful. Please try again later.")
        close_connection(sock_send, sock_recv)
        sys.exit()
    # registration successful (for receiving)

    # user registration successful
    print("User registration successful. Chatting enabled!")

    # create threads for client-side sending and receiving respectively
    try:
        thread_send = threading.Thread(target=send_message, args=(sock_send))
        thread_recv = threading.Thread(target=recv_message, args=(sock_recv))
    except:
        print("Error: There was an issue with multi-threading. Please try again later.")
        close_connection(sock_send, sock_recv)
        sys.exit()

    # start threads
    thread_send.start()
    thread_recv.start()

main()
