# -*- coding: utf-8 -*-

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Date
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

import potcommun



Base = declarative_base()
metadata = Base.metadata

dmgr_persons = Table('dmgr_persons', metadata,
    Column('mgr_oid', Integer, ForeignKey('DebtManagers.oid')),
    Column('person_oid', Integer, ForeignKey('Persons.oid')),
)

persons_payments = Table('persons_payments', metadata,
    Column('person_oid', Integer, ForeignKey('Persons.oid')),
    Column('payments_oid', Integer, ForeignKey('AbstractPayments.oid')),
)

class Person(potcommun.Person, Base):
    __tablename__ = "Persons"
    oid = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    #def __init__(self, name):
        #potcommun.Person.__init__(self, name)
        #Base.__init__(self)

class DebtManager(potcommun.DebtManager, Base):
    __tablename__ = "DebtManagers"
    oid = Column(Integer, primary_key=True)
    persons = relationship(Person, secondary=dmgr_persons, collection_class=set)

    #def __init__(self):
        #potcommun.DebtManager.__init__(self)
        #Base.__init__(self)



    def save(self, handler):
        session = handler.getSession()
        session.begin()
        session.add(self)
        session.commit()



class Outlay(potcommun.Outlay, Base):
    __tablename__ = "Outlays"
    oid = Column(Integer, primary_key=True)
    mgr = Column(Integer, ForeignKey("DebtManagers.oid")) ## Reverse
    date = Column(Date)
    label = Column(String)
    items = relationship("Item", collection_class=set)
    payments = relationship("Payment", collection_class=set)

    #def __init__(self, mgr, date, label):
        #potcommun.Outlay.__init__(self, mgr, date, label)
        #Base.__init__(self)


class AbstractPayment(potcommun.AbstractPayment, Base):

    oid = Column(Integer, primary_key=True)
    classType = Column(String, nullable=False)
    amount = Column(Integer)
    persons = relationship(Person, secondary=persons_payments, collection_class=set)

    __tablename__ = "AbstractPayments"
    __mapper_args__ = {'polymorphic_on': classType}



    #def __init__(self, persons, amount):
        #potcommun.AbstractPayment.__init__(self, persons, amount)
        #Base.__init__(self)


class Payment(potcommun.Payment, Base):

    oid = Column(Integer, ForeignKey("AbstractPayments.oid"), primary_key=True)
    outlay = Column(Integer, ForeignKey("Outlays.oid"))
    __tablename__ = "Payments"
    __mapper_args__ = {'polymorphic_identity': 'payment'}

    #def __init__(self, persons, amount):
        #potcommun.Payment.__init__(self, persons, amount)
        #Base.__init__(self)

class Item(potcommun.Item, Base):

    oid = Column(Integer, ForeignKey("AbstractPayments.oid"), primary_key=True)
    label = Column(String, nullable=False)
    outlay = Column(Integer, ForeignKey("Outlays.oid"))
    __tablename__ = "Items"
    __mapper_args__ = {'polymorphic_identity': 'item'}

    #def __init__(self, persons, label, amount):
        #potcommun.Item.__init__(self, persons, label, amount)
        #Base.__init__(self)

