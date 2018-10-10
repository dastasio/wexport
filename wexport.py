import sqlite3
from os import makedirs, linesep
from os.path import exists
from datetime import datetime
from shutil import copytree, copyfile

ChatList = ['null']
ContactNames = {}

def GetGroupMembers(ChatID, Cursor):
    Members = {}
    Cursor.execute('SELECT jid FROM group_participants WHERE gjid="{ID}"'.format(ID=ChatID))
    JIDs = Cursor.fetchall()

    for JID in JIDs:
        JID = JID[0]
        if not JID:
            continue
        Member = '+' + JID.replace('@s.whatsapp.net', '')
        if JID in ContactNames:
            Member = ContactNames[JID]

        Members[JID] = Member

    return Members

def GetRawMessages(ChatID, Cursor):
    # NOTE(dave): returning both message data and quoted messages' info
    Cursor.execute('SELECT timestamp,data,key_from_me,quoted_row_id,key_id,remote_resource FROM messages WHERE key_remote_jid="{ID}" ORDER BY _id ASC'.format(ID=ChatID))
    RawMessages = Cursor.fetchall()
    Cursor.execute('SELECT _id,key_id FROM messages_quotes WHERE key_remote_jid="{ID}" ORDER BY _id ASC'.format(ID=ChatID))
    RawQuotedMessages = Cursor.fetchall()
    return RawMessages, RawQuotedMessages

# Message format: [0]sender, [1]msg, [2]timestamp, [3]quoted message
def GetMessages(ChatID):
    msgstore = sqlite3.connect('./data/msgstore.db')
    Cur = msgstore.cursor()

    Messages = []
    MESSAGE_TIMESTAMP = 0
    MESSAGE_CONTENT = 1
    MESSAGE_FROM_ME = 2
    MESSAGE_QUOTED = 3
    MESSAGE_KEY_ID = 4
    QUOTE_ID = 0
    QUOTE_KEY_ID = 1

    if '-' in ChatID: # NOTE(dave): If there's a dash in the chat id, it's a group chat
        Self = 'You'
        MESSAGE_SENDER = 5

        RawMessages, RawQuotedMessages = GetRawMessages(ChatID, Cur)
        QuotedIndexes = {}

        Members = GetGroupMembers(ChatID, Cur)

        for Message in RawMessages[1:]:
            # NOTE(dave): We keep track of quoted messages as we find them
            if len(RawQuotedMessages) > 0 and \
                RawQuotedMessages[0][QUOTE_KEY_ID] == Message[MESSAGE_KEY_ID]:
                RawQuote = RawQuotedMessages.pop(0)
                QuotedIndexes[RawQuote[QUOTE_ID]] = len(Messages)

            Sender = Self
            if not Message[MESSAGE_FROM_ME]:
                Sender = Message[MESSAGE_SENDER]
                if not Sender in Members:
                    # TODO(casey): Reactivate this
                    ManualName = 0#input("ATTENTION: display name for " + Sender + " not found. Supply one: ")
                    if ManualName:
                        Members[Sender] = ManualName
                    else:
                        Members[Sender] = '+' + Sender.replace('@s.whatsapp.net', '')
                Sender = Members[Sender]
            
            QuotedMessage = -1
            try:
                QuotedMessage = QuotedIndexes[Message[MESSAGE_QUOTED]]
            except: pass
            Messages.append([Sender, Message[MESSAGE_CONTENT], Message[MESSAGE_TIMESTAMP], QuotedMessage])
    else: # NOTE(dave): No dash: private chat
        Self = 'You'
        Other = ChatID
        try:
            Other = ContactNames[ChatID]
        except: pass
        RawMessages, RawQuotedMessages = GetRawMessages(ChatID, Cur)
        QuotedIndexes = {}

        for Message in RawMessages[1:]:
            # NOTE(dave): We keep track of quoted messages as we find them
            if len(RawQuotedMessages) > 0 and \
            RawQuotedMessages[0][QUOTE_KEY_ID] == Message[MESSAGE_KEY_ID]:
                RawQuote = RawQuotedMessages.pop(0)
                QuotedIndexes[RawQuote[QUOTE_ID]] = len(Messages)

            Sender = Self if Message[MESSAGE_FROM_ME] else Other

            QuotedMessage = -1
            try:
                QuotedMessage = QuotedIndexes[Message[MESSAGE_QUOTED]]
            except: pass
            Messages.append([Sender, Message[MESSAGE_CONTENT], Message[MESSAGE_TIMESTAMP], QuotedMessage])
    msgstore.close()
    return Messages

def HTMLExport(ChatsToExport):
    MESSAGE_SENDER = 0
    MESSAGE_CONTENT = 1
    MESSAGE_TIMESTAMP = 2
    MESSAGE_QUOTED = 3

    TemplatePath = './data/html_templates/'
    OutPath = './exported/html/'
    if not exists(OutPath+'lists/'):
        makedirs(OutPath+'lists/')
    if not exists(OutPath+'images'):
        copytree(TemplatePath + 'images', OutPath + 'images')
    if not exists(OutPath+'js'):
        copytree(TemplatePath+'js', OutPath+'js')
    if not exists(OutPath+'css'):
        copytree(TemplatePath+'css', OutPath+'css')

    ChatsHTMLSource = -1
    with open(TemplatePath+'lists/chats.html', 'r') as f:
        ChatsHTMLSource = f.readlines()
    ChatsHTML = open(OutPath+'lists/chats.html', 'wb')
    while True:
        SourceLine = ChatsHTMLSource.pop(0)
        if SourceLine[0] == '$':
            break
        ChatsHTML.write(SourceLine.encode('utf-8'))
    
    ChatEntryHTMLSource = -1
    with open(TemplatePath+'lists/chat_entry.html', 'rb') as f:
        ChatEntryHTMLSource = f.read()+b'\n'

    ChatCount = 0
    for ChatID in ChatsToExport:
        ChatCount += 1
        ChatName = ChatID.encode('utf-8')
        if ChatID in ContactNames: ChatName = ContactNames[ChatID].encode('utf-8')
        MessagesOutPath = OutPath + 'chats/chat_' + str(ChatCount) + '/'
        if not exists(MessagesOutPath):
            makedirs(MessagesOutPath)

        # TODO(dave): Process messages and export in html
        Messages = GetMessages(ChatID)
        #for Message in Messages:
        copyfile(TemplatePath+'chats/chat_01/messages.html', MessagesOutPath+'messages.html')

        ChatEntryHTML = ChatEntryHTMLSource.\
            replace(b'$CHAT_PATH', 'chat_{0}/messages.html'.format(ChatCount).encode('utf-8'), 1).\
            replace(b'$CHAT_INITIAL', str(ChatName)[0].encode('utf-8'), 1).\
            replace(b'$CHAT_NAME', ChatName, 1).\
            replace(b'$CHAT_LENGTH',str(len(Messages)).encode('utf-8') + b' messages', 1)
        ChatsHTML.write(ChatEntryHTML)
    
    for SourceLine in ChatsHTMLSource:
        ChatsHTML.write(SourceLine.encode('utf-8'))
    ChatsHTML.close()

    # TODO(dave): Edit this file
    copyfile(TemplatePath+'export_results.html', OutPath+'export_results.html')

def PlainTextExport(ChatsToExport):
    MESSAGE_SENDER = 0
    MESSAGE_CONTENT = 1
    MESSAGE_TIMESTAMP = 2
    MESSAGE_QUOTED = 3
    
    for ChatID in ChatsToExport:
        OutPath = './exported/'
        try:
            OutPath += ContactNames[ChatID] + '/'
        except:
            OutPath += ChatID + '/'
        try:
            makedirs(OutPath)
        except: pass

        Messages = GetMessages(ChatID)
        OutFile = "000"
        OutFileMessageCounter = 0
        with open(OutPath + OutFile + '.txt', 'wb') as f:
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
                    f = open(OutPath + OutFile + '.txt', 'wb')

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
    
def PrintChatList():
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
    IDs = []

    for Select in Selections.split(','):
        Select = Select.strip().split('-')
        First = int(Select[0])

        if len(Select) > 1:
            Last = int(Select[1])
            for ChatID in range(First, Last + 1):
                IDs.append(ChatList[ChatID])
        else:
            ChatID = First
            IDs.append(ChatList[ChatID])

    return IDs

def menu():
    Format = int(input('Choose the format[0:html,1:txt]: '))
    SelectedChats = PrintChatList()
    if Format == 0: HTMLExport(SelectedChats)
    elif Format == 1: PlainTextExport(SelectedChats)


if __name__ == "__main__":
    menu()