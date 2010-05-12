# -*- coding: utf-8 -*-
from __future__ import division

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlmodel import metadata, DebtManager, Person, Outlay, Item, Payment

URL = "sqlite:///potcommun.db"

class Handler(object):
    def __init__(self, url=URL, echo=True):
        self.engine = create_engine(url, echo=echo)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.initialize()

    def purge(self):
        metadata.bind = self.engine
        metadata.drop_all()
        self.initialize()

    def initialize(self):
        metadata.bind = self.engine
        metadata.create_all()

    def getSession(self):
        return self.session

    def saveDebtManager(self, debtManager):
        session = self.getSession()
        session.add(debtManager)
        session.commit()
        
    def deleteDebtManager(self, debtManager):
        session = self.getSession()
        session.delete(debtManager)
        session.commit()
        

    def getManagers(self):
        return self.session.query(DebtManager)






