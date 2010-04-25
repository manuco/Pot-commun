# -*- coding: utf-8 -*-
from __future__ import division

from sqlalchemy import create_engine

from sqlmodel import metadata

URL = "sqlite:///potcommun.db"

class Handler(object):
    def __init__(self, url=URL, echo=False):
        self.engine = create_engine(url, echo=echo)
        self.initializeBase()

    def initializeBase(self):
        metadata.create_all(self.engine)













