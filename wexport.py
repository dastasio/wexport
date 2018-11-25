import sqlite3
from os import makedirs, linesep
from os.path import exists
from datetime import datetime
from shutil import copytree, copyfile

ChatList = ['null']
ContactNames = {}

# TODO(dave): Add 'member has left/joined' messages for group chats
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
    Cursor.execute('SELECT timestamp,data,key_from_me,quoted_row_id,key_id,remote_resource,media_wa_type,media_name,media_caption FROM messages WHERE key_remote_jid="{ID}" ORDER BY _id ASC'.format(ID=ChatID))
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
    MESSAGE_SENDER = 5
    MESSAGE_MEDIA_TYPE = 6
    MESSAGE_MEDIA_NAME = 7
    MESSAGE_MEDIA_CAPTION = 8
    QUOTE_ID = 0
    QUOTE_KEY_ID = 1

    if '-' in ChatID: # NOTE(dave): If there's a dash in the chat id, it's a group chat
        Self = 'You'
        
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
            if int(Message[MESSAGE_MEDIA_TYPE]):
                MESSAGE_CONTENT = MESSAGE_MEDIA_CAPTION
            Messages.append([int(Message[MESSAGE_MEDIA_TYPE]), Sender, Message[MESSAGE_CONTENT], Message[MESSAGE_TIMESTAMP], QuotedMessage, -1, Message[MESSAGE_MEDIA_NAME]])
            MESSAGE_CONTENT = 1
            # NOTE(dave): Message Struct
            # [0]Media type, [1]Sender, [2]Content, [3]Timestamp, [4]Quoted message index, 
            # [5]Message Unique ID (to be filled later), [6]Media filename
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
            if int(Message[MESSAGE_MEDIA_TYPE]):
                MESSAGE_CONTENT = MESSAGE_MEDIA_CAPTION
            Messages.append([int(Message[MESSAGE_MEDIA_TYPE]), Sender, Message[MESSAGE_CONTENT], Message[MESSAGE_TIMESTAMP], QuotedMessage, -1, Message[MESSAGE_MEDIA_NAME]])
            MESSAGE_CONTENT = 1
            # NOTE(dave): Message Struct
            # [0]Media type, [1]Sender, [2]Content, [3]Timestamp, [4]Quoted message index, 
            # [5]Message Unique ID (to be filled later), [6]Media filename
    msgstore.close()
    return Messages

def HTMLExport(ChatsToExport):
    # TODO(dave): maybe fix naming inconsistencies
    MESSAGE_TYPE = 0
    MESSAGE_SENDER = 1
    MESSAGE_CONTENT = 2
    MESSAGE_TIMESTAMP = 3
    MESSAGE_QUOTED = 4
    MESSAGE_ID = 5
    MESSAGE_FILENAME = 6
    TYPE_IMAGE = 1
    TYPE_VOICE = 2
    TYPE_VIDEO = 3
    TYPE_DELETED = 15

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
    
    MessagesHTMLSource = -1
    with open(TemplatePath+'chats/messages.html', 'rb') as f:
        MessagesHTMLSource = f.read()+b'\n'

    MessageEntryHTMLSource = -1
    with open(TemplatePath+'chats/message_entry.html', 'rb') as f:
        MessageEntryHTMLSource = f.read()+b'\n'
    
    MessageEntryJoinedHTMLSource = -1
    with open(TemplatePath+'chats/message_entry_joined.html', 'rb') as f:
        MessageEntryJoinedHTMLSource = f.read()+b'\n'

    MessageDateHTMLSource = -1
    with open(TemplatePath+'chats/message_date.html', 'rb') as f:
        MessageDateHTMLSource = f.read()+b'\n'

    PageLinkHTMLSource = b'\t\t\t\t<a class="pagination block_link" href="messages$PAGE_LINK.html">\n \
                        $LINK_TEXT\n \
                        \t\t\t\t</a>\n\n'
    
    # TODO(dave): Maybe change 'this message' to quoted message's sender
    QuoteHTMLSource = b'\t\t\t\t\t\t<div class="reply_to details"> \n\
                        \t\t\t\t\t\t\tIn reply to <a href="#go_to_message$QUOTED_ID" onclick="return GoToMessage($QUOTED_ID)">this message</a> \n\
                        \t\t\t\t\t\t</div>\n'

    ImageHTMLSource = b'\t\t\t\t\t\t<div class="media_wrap clearfix"> \n\
                        \t\t\t\t\t\t\t<a class="photo_wrap clearfix pull_left" href="./photos/$FILENAME"> \n\
                        \t\t\t\t\t\t\t\t<img class="photo" src="./photos/$FILENAME" \n\
                        \t\t\t\t\t\t\t\t\tstyle="width: 146px; height: 260px" /> \n\
                        \t\t\t\t\t\t\t</a> \n\
                        \t\t\t\t\t\t</div>\n'
    VoiceHTMLSource = b'\t\t\t\t\t\t<div class="media_wrap clearfix"> \n\
                        \t\t\t\t\t\t\t<a class="media clearfix pull_left block_link media_voice_message" href="./voice_messages/$FILENAME"> \n\
                        \t\t\t\t\t\t\t\t<div class="fill pull_left"> \n\
                        \t\t\t\t\t\t\t\t</div> \n\
                        \t\t\t\t\t\t\t\t<div class="body"> \n\
                        \t\t\t\t\t\t\t\t\t<div class="title bold"> \n\
                        \t\t\t\t\t\t\t\t\t\tVoice message \n\
                        \t\t\t\t\t\t\t\t\t</div> \n\
                        \t\t\t\t\t\t\t\t\t<div class="status details"> \n\
                        $DURATION \n\
                        \t\t\t\t\t\t\t\t\t</div> \n\
                        \t\t\t\t\t\t\t\t</div> \n\
                        \t\t\t\t\t\t\t</a> \n\
                        \t\t\t\t\t\t</div>\n'
    VideoHTMLSource = b'\t\t\t\t\t\t<a class="video_file_wrap clearfix pull_left" href="./video_files/$FILENAME"> \n\
                        \t\t\t\t\t\t\t<div class="video_play_bg"> \n\
                        \t\t\t\t\t\t\t\t<div class="video_play"> \n\
                        \t\t\t\t\t\t\t\t</div> \n\
                        \t\t\t\t\t\t\t</div> \n\
                        \t\t\t\t\t\t\t<div class="video_duration"> \n\
                        $DURATION \n\
                        \t\t\t\t\t\t\t</div> \n\
                        \t\t\t\t\t\t\t<img class="video_file" src="./video_files/$THUMBNAIL" style="width: 260px; height: 145px"/> \n\
                        \t\t\t\t\t\t</a>\n'
    ChatCount = 0
    MessagesTotalCount = 0
    for ChatID in ChatsToExport:
        ChatCount += 1
        ChatName = ChatID.encode('utf-8')
        if ChatID in ContactNames: ChatName = ContactNames[ChatID].encode('utf-8')
        MessagesOutPath = OutPath + 'chats/chat_' + str(ChatCount) + '/'
        if not exists(MessagesOutPath):
            makedirs(MessagesOutPath)

        
        Messages = GetMessages(ChatID)
        OldDateDay = -1
        OldSender = -1
        PageHTML = b''
        PageMessageCount = 0
        PageCount = 1
        for Message in Messages:
            MessagesTotalCount += 1
            PageMessageCount += 1
            DateDay = datetime.fromtimestamp(Message[MESSAGE_TIMESTAMP]/1000).strftime("%d %B %Y").encode('utf-8')
            DateTime = datetime.fromtimestamp(Message[MESSAGE_TIMESTAMP]/1000).strftime("%H:%M:%S").encode('utf-8')
            DateComplete = DateDay + b' ' + DateTime
            DateTime = DateTime[:-3]
            # TODO(dave): check that this works as expected ^^^
            Sender = Message[MESSAGE_SENDER].replace('@s.whatsapp.net','').encode('utf-8') if Message[MESSAGE_SENDER] != 'MeMedesimo' else b'You'
            Content = Message[MESSAGE_CONTENT].encode('utf-8') if Message[MESSAGE_CONTENT] else b''
            QuoteHTML = b''
            MediaHTML = b''

            # TODO(dave): Manage quotes
            # TODO(dave): Add/remove previous/next messages link
            MessageEntryHTML = b''
            if DateDay != OldDateDay:
                MessageEntryHTML += MessageDateHTMLSource.\
                    replace(b'$MESSAGE_ID', str(MessagesTotalCount).encode('utf-8'), 1).\
                    replace(b'$CHAT_DATE', DateDay, 1)
                MessagesTotalCount += 1
                OldDateDay = DateDay
            
            Message[MESSAGE_ID] = MessagesTotalCount
            if Message[MESSAGE_QUOTED] > -1:
                QuotedIndex = Message[MESSAGE_QUOTED]
                QuotedID = Messages[QuotedIndex][MESSAGE_ID]
                QuoteHTML = QuoteHTMLSource.\
                    replace(b'$QUOTED_ID', str(QuotedID).encode('utf-8'), 2)
            if Message[MESSAGE_TYPE] == TYPE_DELETED:
                Content = b'~deleted message~'
            elif Message[MESSAGE_TYPE] == TYPE_VIDEO:
                # TODO(dave): Insert video duration
                MediaHTML = VideoHTMLSource.\
                    replace(b'$FILENAME', b'test.mp4', 1).\
                    replace(b'$DURATION', b'00:00', 1).\
                    replace(b'$THUMBNAIL', b'test_thumb.jpg', 1)
            elif Message[MESSAGE_TYPE] == TYPE_VOICE:
                # TODO(dave): Insert voice duration
                MediaHTML = VoiceHTMLSource.\
                    replace(b'$FILENAME', b'test.opus', 1)
            elif Message[MESSAGE_TYPE] == TYPE_IMAGE:
                # TODO(dave): Add thumbnails
                # TODO(dave): Make thumbnail size dynamic
                # TODO(dave): Copy images from source to destination
                MediaHTML = ImageHTMLSource.\
                    replace(b'$FILENAME', b'test.jpg', 2)
            if Sender != OldSender:
                MessageInitials = bytes([Sender[0]])
                # TODO(dave): make color more random
                MessageInitialColor = ((Sender[0] + ChatCount) % 7) + 1
                MessageEntryHTML += MessageEntryHTMLSource.\
                    replace(b'$MESSAGE_ID', str(Message[MESSAGE_ID]).encode('utf-8'), 1).\
                    replace(b'$MESSAGE_INITIALS_COLOR', str(MessageInitialColor).encode('utf-8'), 1).\
                    replace(b'$MESSAGE_INITIALS', MessageInitials, 1).\
                    replace(b'$MESSAGE_TIME_COMPLETE', DateComplete, 1).\
                    replace(b'$MESSAGE_TIME', DateTime, 1).\
                    replace(b'$QUOTE', QuoteHTML, 1).\
                    replace(b'$MESSAGE_SENDER', Sender, 1).\
                    replace(b'$MESSAGE_MEDIA', MediaHTML, 1).\
                    replace(b'$MESSAGE_CONTENT', Content, 1)
                OldSender = Sender
            else:
                MessageEntryHTML += MessageEntryJoinedHTMLSource.\
                    replace(b'$MESSAGE_ID', str(Message[MESSAGE_ID]).encode('utf-8'), 1).\
                    replace(b'$MESSAGE_TIME_COMPLETE', DateComplete, 1).\
                    replace(b'$MESSAGE_TIME', DateTime, 1).\
                    replace(b'$QUOTE', QuoteHTML, 1).\
                    replace(b'$MESSAGE_MEDIA', MediaHTML, 1).\
                    replace(b'$MESSAGE_CONTENT', Content, 1)
            
            PageHTML += MessageEntryHTML
            if PageMessageCount >= 700:
                PageNumber = b'' if PageCount==1 else str(PageCount).encode('utf-8')
                NextPageNumber = str(PageCount+1).encode('utf-8')
                PrevPageNumber = b'' if PageCount<=2 else str(PageCount-1).encode('utf-8')
                if PageCount > 1:
                    PageHTML = PageLinkHTMLSource.\
                        replace(b'$PAGE_LINK', PrevPageNumber, 1).\
                        replace(b'$LINK_TEXT', b'Previous messages', 1) + PageHTML
                # TODO(dave): Check if 'next messages' link is actually needed
                PageHTML += PageLinkHTMLSource.\
                    replace(b'$PAGE_LINK', NextPageNumber, 1).\
                    replace(b'$LINK_TEXT', b'Next messages', 1)
                MessagesHTML = MessagesHTMLSource.\
                    replace(b'$CHAT_NAME', ChatName, 1).\
                    replace(b'$MESSAGE_LIST', PageHTML, 1)

                
                MessagesFile = open(MessagesOutPath+'messages{0}.html'.format(PageNumber.decode('utf-8')), 'wb')
                MessagesFile.write(MessagesHTML)
                MessagesFile.close()
                PageCount += 1
                PageMessageCount = 0
                PageHTML = b''
                OldDateDay = -1
                OldSender = -1
            
        # TODO(dave): compress this
        PageNumber = b'' if PageCount==1 else str(PageCount).encode('utf-8')
        PrevPageNumber = b'' if PageCount<=2 else str(PageCount-1).encode('utf-8')
        if PageCount > 1:
            PageHTML = PageLinkHTMLSource.\
                replace(b'$PAGE_LINK', PrevPageNumber, 1).\
                replace(b'$LINK_TEXT', b'Previous messages', 1) + PageHTML
        MessagesHTML = MessagesHTMLSource.\
            replace(b'$CHAT_NAME', ChatName, 1).\
            replace(b'$MESSAGE_LIST', PageHTML, 1)
        
        MessagesFile = open(MessagesOutPath+'messages{0}.html'.format(PageNumber.decode('utf-8')), 'wb')
        MessagesFile.write(MessagesHTML)
        MessagesFile.close()
        PageCount += 1
        PageHTML = b''

        ChatInitial = bytes([ChatName[0]])
        ChatInitialColor = (ChatName[0] % 7) + 1
        ChatEntryHTML = ChatEntryHTMLSource.\
            replace(b'$CHAT_PATH', 'chat_{0}/messages.html'.format(ChatCount).encode('utf-8'), 1).\
            replace(b'$CHAT_INITIAL_COLOR', str(ChatInitialColor).encode('utf-8'), 1).\
            replace(b'$CHAT_INITIAL', ChatInitial, 1).\
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