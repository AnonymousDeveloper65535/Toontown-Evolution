from pandac.PandaModules import *

from direct.distributed.DistributedObjectGlobal import DistributedObjectGlobal

from toontown.chat.WhisperPopup import WhisperPopup
from toontown.chat.ChatGlobals import WTSystem

from otp.distributed.PotentialAvatar import PotentialAvatar
from otp.otpbase import OTPGlobals

import time


def generateLookupTable(timestamp):
    # Strip the last 4 digits out of the timestamp:
    stripped = int(str(int(timestamp))[:-4])

    # Create the lookup table:
    return [hex(int(str(stripped)[i % len(str(stripped))]) & stripped & i) for i in xrange(255)]


def encodeHexString(lookupTable, hexString):
    return ''.join(lookupTable[int('0x%s' % i, 16)] for i in hexString.split('0x')[1:])


class ClientServicesManager(DistributedObjectGlobal):
    notify = directNotify.newCategory('ClientServicesManager')

    def __init__(self, cr):
        DistributedObjectGlobal.__init__(self, cr)

        self.loginDoneEvent = None
        self.systemMessageSfx = None

    # --- LOGIN LOGIC ---
    def performLogin(self, doneEvent):
        self.loginDoneEvent = doneEvent
        self.sendUpdate('requestAuthToken')

    def receiveAuthToken(self, authToken):
        lookupTable = generateLookupTable(time.time())
        self.sendUpdate('login', [self.cr.playToken or 'dev', encodeHexString(lookupTable, authToken)])
        del lookupTable

    def acceptLogin(self, timestamp):
        messenger.send(self.loginDoneEvent, [{'mode': 'success', 'timestamp': timestamp}])
        self.loginDoneEvent = None

    # --- AVATARS LIST ---
    def requestAvatars(self):
        self.sendUpdate('requestAvatars')

    def setAvatars(self, avatars):
        avList = []
        for avNum, avName, avDNA, avPosition, nameState in avatars:
            nameOpen = int(nameState == 1)
            names = [avName, '', '', '']
            if nameState == 2:  # PENDING
                names[1] = avName
            elif nameState == 3:  # APPROVED
                names[2] = avName
            elif nameState == 4:  # REJECTED
                names[3] = avName
            avList.append(PotentialAvatar(avNum, names, avDNA, avPosition, nameOpen))

        self.cr.handleAvatarsList(avList)

    # --- AVATAR CREATION/DELETION ---
    def sendCreateAvatar(self, avDNA, _, index):
        self.sendUpdate('createAvatar', [avDNA.makeNetString(), index])

    def createAvatarResp(self, avId):
        messenger.send('nameShopCreateAvatarDone', [avId])

    def sendDeleteAvatar(self, avId):
        self.sendUpdate('deleteAvatar', [avId])

    # No deleteAvatarResp; it just sends a setAvatars when the deed is done.

    # --- AVATAR NAMING ---
    def sendSetNameTyped(self, avId, name, callback):
        self._callback = callback
        self.sendUpdate('setNameTyped', [avId, name])

    def setNameTypedResp(self, avId, status):
        self._callback(avId, status)

    def sendSetNamePattern(self, avId, p1, f1, p2, f2, p3, f3, p4, f4, callback):
        self._callback = callback
        self.sendUpdate('setNamePattern', [avId, p1, f1, p2, f2, p3, f3, p4, f4])

    def setNamePatternResp(self, avId, status):
        self._callback(avId, status)

    def sendAcknowledgeAvatarName(self, avId, callback):
        self._callback = callback
        self.sendUpdate('acknowledgeAvatarName', [avId])

    def acknowledgeAvatarNameResp(self):
        self._callback()

    # --- AVATAR CHOICE ---
    def sendChooseAvatar(self, avId):
        self.sendUpdate('chooseAvatar', [avId])

    def systemMessage(self, message):
        whisper = WhisperPopup(message, OTPGlobals.getInterfaceFont(), WTSystem)
        whisper.manage(base.marginManager)

        if self.systemMessageSfx is None:
            self.systemMessageSfx = base.loadSfx('phase_3/audio/sfx/clock03.ogg')

        base.playSfx(self.systemMessageSfx)
