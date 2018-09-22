import sqlite3
from os import makedirs, linesep
from datetime import datetime

ChatList = ['null']
ContactNames = {}

def PlainTestChat(ChatID):
    MESSAGE_SENDER = 0
    MESSAGE_CONTENT = 1
    MESSAGE_TIMESTAMP = 2
    MESSAGE_QUOTED = 3
    Messages = [
        # sender    |   msg |   timestamp   |   quoted message
        ['MeMedesimo',  'one😡',  123456789,      -1],
        ['Altro',       'two',  234586901,      -1],
        ['MeMedesimo',  'three', 123456799,      1],
        ['Altro',       0,      1234,            2]
    ]

    # TODO(dave): check that directory doesn't already exist
    OutPath = './exported/' + ChatList[ChatID]
    makedirs(OutPath)
    with open(OutPath + '/00.txt', 'wb') as f:
        for Message in Messages:
            Time = datetime.utcfromtimestamp(Message[MESSAGE_TIMESTAMP]/1000).strftime("%Y-%m-%d %H:%M:%S")
            Sender = Message[MESSAGE_SENDER] if Message[MESSAGE_SENDER] != "MeMedesimo" else "You"
            # TODO(dave): Specify type of data
            Content = Message[MESSAGE_CONTENT] if Message[MESSAGE_CONTENT] else '~~MEDIA~~'
            MessageExport = '[' + Time + '] ' + Sender + ': ' + str(Content) + linesep
            f.write(MessageExport.encode('utf8'))

def CleanChatID(ID):
    return ID.replace('@g.us', '').replace('@s.whatsapp.net', '')

def GetChatList():
    # NOTE(dave): Getting contact names
    wa = sqlite3.connect('./data/wa.db')
    Cur = wa.cursor()
    Cur.execute('SELECT jid,display_name FROM wa_contacts WHERE is_whatsapp_user=1 AND raw_contact_id>0')
    Result = Cur.fetchall()
    for elem in Result:
        ContactNames[CleanChatID(elem[0])] = elem[1]
    wa.close()

    msgstore = sqlite3.connect('./data/msgstore.db')
    Cur = msgstore.cursor()
    Cur.execute('SELECT key_remote_jid,subject FROM chat_list')
    Result = Cur.fetchall()
    for elem in Result:
        ChatList.append(CleanChatID(elem[0]))
        if elem[1]:
            ContactNames[CleanChatID(elem[0])] = elem[1]
    msgstore.close()
    
def menu():
    GetChatList()
    '''
    print('Detected following conversations:')
    for i in range(1, len(ChatList)):
        print(str(i) + '. ' + ChatList[i])

    Selections = input('\nWhich conversation would you like to export? ')
    
    for Select in Selections.split(','):
        Select = Select.strip().split('-')
        First = int(Select[0])

        if len(Select) > 1:
            Last = int(Select[1])
            for ChatID in range(First, Last + 1):
                PlainTestChat(ChatID)
        else:
            ChatID = First
            PlainTestChat(ChatID)
    '''
        
        


if __name__ == "__main__":
    menu()