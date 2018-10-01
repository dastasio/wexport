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
        MESSAGE_TIMESTAMP = 0
        MESSAGE_CONTENT = 1
        MESSAGE_FROM_ME = 2
        MESSAGE_QUOTED = 3
        MESSAGE_KEY_ID = 4
        QUOTE_ID = 0
        QUOTE_KEY_ID = 1

        Self = 'You'
        Other = ChatID
        try:
            Other = ContactNames[ChatID]
        except: pass
        # NOTE(dave): we need to get both message data and quoted messages' info
        Cur.execute('SELECT timestamp,data,key_from_me,quoted_row_id,key_id FROM messages WHERE key_remote_jid="{ID}" ORDER BY _id ASC'.format(ID=ChatID))
        RawMessages = Cur.fetchall()
        Cur.execute('SELECT _id,key_id FROM messages_quotes WHERE key_remote_jid="{ID}" ORDER BY _id ASC'.format(ID=ChatID))
        RawQuotedMessages = Cur.fetchall()
        QuotedIndexes = {}

        for Message in RawMessages[1:]:
            # NOTE(dave): We keep track of quoted messages as we find them
            if len(RawQuotedMessages) > 0 and \
                RawQuotedMessages[0][QUOTE_KEY_ID] == Message[MESSAGE_KEY_ID]:
                RawQuote = RawQuotedMessages.pop(0)
                QuotedIndexes[RawQuote[QUOTE_ID]] = len(Messages)

            Sender = Self if Message[MESSAGE_FROM_ME] else Other
            if Message[MESSAGE_QUOTED]:
                pass
            QuotedMessage = -1
            try:
                QuotedMessage = QuotedIndexes[Message[MESSAGE_QUOTED]]
            except: pass
            Messages.append([Sender, Message[MESSAGE_CONTENT], Message[MESSAGE_TIMESTAMP], QuotedMessage])
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
    except: pass
    # TODO(dave): divide long chats in different files
    OutFile = "000"
    OutFileMessageCounter = 0
    with open(OutPath + '/' + OutFile + '.txt', 'wb') as f:
        for Message in Messages:
            Time = datetime.fromtimestamp(Message[MESSAGE_TIMESTAMP]/1000).strftime("%Y-%m-%d %H:%M:%S")
            Sender = Message[MESSAGE_SENDER].replace('@s.whatsapp.net','') if Message[MESSAGE_SENDER] != "MeMedesimo" else "You"
            # TODO(dave): Specify type of data
            # TODO(dave): Manage data
            Content = Message[MESSAGE_CONTENT] if Message[MESSAGE_CONTENT] else '~~MEDIA~~'
            Quote = ''
            if Message[MESSAGE_QUOTED] > -1:
                QuotedIndex = Message[MESSAGE_QUOTED]
                QuotedContent = Messages[QuotedIndex][MESSAGE_CONTENT] if Messages[QuotedIndex][MESSAGE_CONTENT] else '~~MEDIA~~'
                QuotedSender = Messages[QuotedIndex][MESSAGE_SENDER] if Messages[QuotedIndex][MESSAGE_SENDER] != "MeMedesimo" else "You"
                Quote = linesep + '           {In reply to ' + QuotedSender + ': ' + QuotedContent + '}'
            MessageLead = '[' + Time + '] ' + Sender + ': '
            MessageEnd = Quote + linesep
            MessageLines = Content.split('\n')
            MessageExport = MessageLead + MessageLines[0]
            for Line in MessageLines[1:]:
                MessageExport = MessageExport + linesep + ' '*len(MessageLead) + Line
            MessageExport = MessageExport + MessageEnd
            f.write(MessageExport.encode('utf8'))

            if '\n' in Content:
                pass# print("FOUND NEWLINE: " + str(Content))
            OutFileMessageCounter = OutFileMessageCounter + 1
            if OutFileMessageCounter >= 500:
                OutFile = '{0:03d}'.format(int(OutFile) + 1)
                OutFileMessageCounter = 0
                f.close()
                f = open(OutPath + '/' + OutFile + '.txt', 'wb')

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