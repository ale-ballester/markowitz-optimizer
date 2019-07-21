from enum import Enum
import logging
import random
from pyfix.connection import ConnectionState, MessageDirection
from pyfix.client_connection import FIXClient
from pyfix.engine import FIXEngine
from pyfix.message import FIXMessage
from pyfix.event import TimerEventRegistration

# https://github.com/wannabegeek/PyFIX
# https://hackernoon.com/9-great-tools-for-algo-trading-e0938a6856cd

class Side(Enum):
    buy = 1
    sell = 2

class Client(FIXEngine):

    def __init__(self):
        FIXEngine.__init__(self, "client_example.store")
        self.client_order_ID = 0
        self.msg_generator = None

        # create a FIX Client using the FIX 4.4 standard
        self.client = FIXClient(self, "pyfix.FIX44", "TARGET", "SENDER")

        # we register some listeners since we want to know when the connection goes up or down
        self.client.addConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.client.addConnectionListener(self.onDisconnect, ConnectionState.DISCONNECTED)

        # start our event listener indefinitely
        self.client.start('localhost', int("9898"))
        while True:
            self.eventManager.waitForEventWithTimeout(10.0)

        # some clean up before we shut down
        self.client.removeConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.client.removeConnectionListener(self.onConnect, ConnectionState.DISCONNECTED)

    def onConnect(self, session):
        logging.info("Established connection to %s" % (session.address(), ))
        # register to receive message notifications on the session which has just been created
        session.addMessageHandler(self.onLogin, MessageDirection.INBOUND, self.client.protocol.msgtype.LOGON)
        session.addMessageHandler(self.onExecutionReport, MessageDirection.INBOUND, self.client.protocol.msgtype.EXECUTIONREPORT)

    def onDisconnect(self, session):
        logging.info("%s has disconnected" % (session.address(), ))
        # we need to clean up our handlers, since this session is disconnected now
        session.removeMessageHandler(self.onLogin, MessageDirection.INBOUND, self.client.protocol.msgtype.LOGON)
        session.removeMessageHandler(self.onExecutionReport, MessageDirection.INBOUND, self.client.protocol.msgtype.EXECUTIONREPORT)
        if self.msg_generator:
            self.eventManager.unregisterHandler(self.msg_generator)

    def sendOrder(self, connectionHandler):
        self.client_order_ID = self.client_order_ID + 1
        codec = connectionHandler.codec
        msg = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
        msg.setField(codec.protocol.fixtags.Price, "%0.2f" % (random.random() * 2 + 10))
        msg.setField(codec.protocol.fixtags.OrderQty, int(random.random() * 100))
        msg.setField(codec.protocol.fixtags.Symbol, "VOD.L")
        msg.setField(codec.protocol.fixtags.SecurityID, "GB00BH4HKS39")
        msg.setField(codec.protocol.fixtags.SecurityIDSource, "4")
        msg.setField(codec.protocol.fixtags.Account, "TEST")
        msg.setField(codec.protocol.fixtags.HandlInst, "1")
        msg.setField(codec.protocol.fixtags.ExDestination, "XLON")
        msg.setField(codec.protocol.fixtags.Side, int(random.random() * 2) + 1)
        msg.setField(codec.protocol.fixtags.client_order_ID, str(self.client_order_ID))
        msg.setField(codec.protocol.fixtags.Currency, "GBP")

        connectionHandler.sendMsg(msg)
        side = Side(int(msg.getField(codec.protocol.fixtags.Side)))
        logging.debug("---> [%s] %s: %s %s %s@%s" % (codec.protocol.msgtype.msgTypeToName(msg.msgType), msg.getField(codec.protocol.fixtags.client_order_ID), msg.getField(codec.protocol.fixtags.Symbol), side.name, msg.getField(codec.protocol.fixtags.OrderQty), msg.getField(codec.protocol.fixtags.Price)))


    def onLogin(self, connectionHandler, msg):
        logging.info("Logged in")

        # lets do something like send and order every 3 seconds
        self.msg_generator = TimerEventRegistration(lambda type, closure: self.sendOrder(closure), 0.5, connectionHandler)
        self.eventManager.registerHandler(self.msg_generator)

    def onExecutionReport(self, connectionHandler, msg):
        codec = connectionHandler.codec
        if codec.protocol.fixtags.ExecType in msg:
            if msg.getField(codec.protocol.fixtags.ExecType) == "0":
                side = Side(int(msg.getField(codec.protocol.fixtags.Side)))
                logging.debug("<--- [%s] %s: %s %s %s@%s" % (codec.protocol.msgtype.msgTypeToName(msg.getField(codec.protocol.fixtags.MsgType)), msg.getField(codec.protocol.fixtags.client_order_ID), msg.getField(codec.protocol.fixtags.Symbol), side.name, msg.getField(codec.protocol.fixtags.OrderQty), msg.getField(codec.protocol.fixtags.Price)))
            elif msg.getField(codec.protocol.fixtags.ExecType) == "4":
                reason = "Unknown" if codec.protocol.fixtags.Text not in msg else msg.getField(codec.protocol.fixtags.Text)
                logging.info("Order Rejected '%s'" % (reason,))
        else:
            logging.error("Received execution report without ExecType")

def main():
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
    client = Client()
    logging.info("All done... shutting down")

if __name__ == '__main__':
    main()