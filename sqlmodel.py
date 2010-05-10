# -*- coding: utf-8 -*-

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Date
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

import potcommun

Base = declarative_base()
metadata = Base.metadata

dmgr_persons = Table('dmgr_persons', metadata,
    Column('mgr_oid', Integer, ForeignKey('DebtManagers.oid')),
    Column('person_oid', Integer, ForeignKey('Persons.name')),
)

persons_payments = Table('persons_payments', metadata,
    Column('person_oid', Integer, ForeignKey('Persons.name')),
    Column('payments_oid', Integer, ForeignKey('AbstractPayments.oid')),
)

class Person(potcommun.Person, Base):
    __tablename__ = "Persons"
    name = Column(String, primary_key=True, nullable=False, unique=True)

class DebtManager(potcommun.DebtManager, Base):
    __tablename__ = "DebtManagers"
    oid = Column(Integer, primary_key=True)
    name = Column(String)
    persons = relationship(Person, secondary=dmgr_persons, collection_class=set)
    outlays = relationship("Outlay", collection_class=set)

class Outlay(potcommun.Outlay, Base):
    __tablename__ = "Outlays"
    oid = Column(Integer, primary_key=True)
    mgr = Column(Integer, ForeignKey("DebtManagers.oid")) ## Reverse
    date = Column(Date)
    label = Column(String)
    items = relationship("Item", collection_class=set)
    payments = relationship("Payment", collection_class=set)

class AbstractPayment(potcommun.AbstractPayment, Base):

    oid = Column(Integer, primary_key=True)
    classType = Column(String, nullable=False)
    amount = Column(Integer)
    outlay = Column(Integer, ForeignKey("Outlays.oid"))
    persons = relationship(Person, secondary=persons_payments, collection_class=set)

    __tablename__ = "AbstractPayments"
    __mapper_args__ = {
        'polymorphic_on': classType,
    }

class Payment(potcommun.Payment, AbstractPayment):

    oid = Column(Integer, ForeignKey("AbstractPayments.oid"), primary_key=True)
    __tablename__ = "Payments"
    __mapper_args__ = {
        'polymorphic_identity': 'payment',
    }

class Item(potcommun.Item, AbstractPayment):

    oid = Column(Integer, ForeignKey("AbstractPayments.oid"), primary_key=True)
    label = Column(String, nullable=False)
    __tablename__ = "Items"
    __mapper_args__ = {
        'polymorphic_identity': 'item',
    }

