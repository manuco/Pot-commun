# -*- coding: utf-8 -*-
from __future__ import division

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Date
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

import potcommun

URL = "sqlite:///potcommun.db"

Base = declarative_base()
metadata = Base.metadata

dmgr_persons = Table('dmgr_persons', metadata,
    Column('mgr_oid', Integer, ForeignKey('DebtManager.oid')),
    Column('person_oid', Integer, ForeignKey('Person.oid')),
)

persons_payments = Table('persons_payments', metadata,
    Column('person_oid', Integer, ForeignKey('Person.oid')),
    Column('payments_oid', Integer, ForeignKey('AbstractPayment.oid')),
)

class Person(potcommun.Person, Base):
    __tablename__ = "Persons"
    oid = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

class DebtManager(potcommun.DebtManager, Base):
    __tablename__ = "DebtManagers"
    oid = Column(Integer, primary_key=True)
    persons = relationship(Person, secondary=dmgr_persons)

class Outlay(potcommun.Outlay, Base):
    __tablename__ = "Outlays"
    oid = Column(Integer, primary_key=True)
    mgr = Column(Integer, ForeignKey(DebtManager.oid)) ## Reverse
    date = Column(Date)
    label = Column(String)

class AbstractPayment(potcommun.AbstractPayment, Base):
    __tablename__ = "AbstractPayments"
    oid = Column(Integer, primary_key=True)
    classType = Column(String, nullable=False)
    amount = Column(Integer)
    persons =  relationship(Person, secondary=persons_payments)

class Payment(potcommun.Payment, Base):
    __tablename__ = "Payments"
    oid = Column(Integer, ForeignKey(AbstractPayment.oid), primary_key=True)
    outlay = Column(Integer, ForeignKey(Outlay.oid), backref="payments")

class Item(potcommun.Item, Base):
    __tablename__ = "Items"
    oid = Column(Integer, ForeignKey(AbstractPayment.oid), primary_key=True)
    label = Column(String, nullable=False)
    outlay = Column(Integer, ForeignKey(Outlay.oid), backref="items")














