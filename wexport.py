import sqlite3
from os import makedirs, linesep
from datetime import datetime

ChatList = ['null']
ContactNames = {}

# Message format: [0]sender, [1]msg, [2]timestamp, [3]quoted message
def GetMessages(ChatID):
    msgstore = sqlite3.connect('./data/msgstore.db')
    Cur = msgstore.cursor()

    Messages = []
    # NOTE(dave): If there's a dash in the chat id, it's a group chat
    if '-' in ChatID:
        pass
    # NOTE(dave): No dash: private chat
    else:
        Self = 'You'
        Other = ChatID
        try:
            Other = ContactNames[ChatID]
        except:
            pass
        Cur.execute('SELECT timestamp,data,key_from_me FROM messages WHERE key_remote_jid="{ID}" ORDER BY _id ASC'.format(ID=ChatID))
        RawMessages = Cur.fetchall()

        for Message in RawMessages[1:]:
            Sender = Self if Message[2] else Other
            Messages.append([Sender, Message[1], Message[0], -1])
    return Messages


def PlainTestChat(ChatID):
    MESSAGE_SENDER = 0
    MESSAGE_CONTENT = 1
    MESSAGE_TIMESTAMP = 2
    MESSAGE_QUOTED = 3
    Messages = GetMessages(ChatID)

    # TODO(dave): check that directory doesn't already exist
    OutPath = './exported/'
    try:
        OutPath += ContactNames[ChatID]
    except:
        OutPath += ChatID
    try:
        makedirs(OutPath)
    except:
        pass
    # TODO(dave): divide long chats in different files
    with open(OutPath + '/00.txt', 'wb') as f:
        for Message in Messages:
            Time = datetime.fromtimestamp(Message[MESSAGE_TIMESTAMP]/1000).strftime("%Y-%m-%d %H:%M:%S")
            Sender = Message[MESSAGE_SENDER] if Message[MESSAGE_SENDER] != "MeMedesimo" else "You"
            # TODO(dave): Specify type of data
            # TODO(dave): Manage data
            Content = Message[MESSAGE_CONTENT] if Message[MESSAGE_CONTENT] else '~~MEDIA~~'
            MessageExport = '[' + Time + '] ' + Sender + ': ' + str(Content) + linesep
            f.write(MessageExport.encode('utf8'))

def GetChatList():
    # NOTE(dave): Getting contact names
    wa = sqlite3.connect('./data/wa.db')
    Cur = wa.cursor()
    Cur.execute('SELECT jid,display_name FROM wa_contacts WHERE is_whatsapp_user=1 AND raw_contact_id>0')
    Result = Cur.fetchall()
    for elem in Result:
        ContactNames[elem[0]] = elem[1]
    wa.close()

    msgstore = sqlite3.connect('./data/msgstore.db')
    Cur = msgstore.cursor()
    Cur.execute('SELECT key_remote_jid,subject FROM chat_list')
    Result = Cur.fetchall()
    for elem in Result:
        ChatList.append(elem[0])
        if elem[1]:
            ContactNames[elem[0]] = elem[1]
    msgstore.close()
    
def menu():
    GetChatList()
    
    print('Detected following conversations:')
    for i in range(1, len(ChatList)):
        ChatID = ChatList[i]
        try:
            ChatID = ContactNames[ChatID]
        except:
            pass
        print(str(i) + '. ' + ChatID)

    Selections = input('\nWhich conversation would you like to export? ')
    
    for Select in Selections.split(','):
        Select = Select.strip().split('-')
        First = int(Select[0])

        if len(Select) > 1:
            Last = int(Select[1])
            for ChatID in range(First, Last + 1):
                PlainTestChat(ChatList[ChatID])
        else:
            ChatID = First
            PlainTestChat(ChatList[ChatID])
    
        
        


if __name__ == "__main__":
    menu()