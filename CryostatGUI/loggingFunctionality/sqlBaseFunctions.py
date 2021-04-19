"""Utility Classes for the sqlite database logging

Most of this is adapted from: https://github.com/alistair-broomhead/python-logging-proxy


The MIT License (MIT)

Copyright (c) 2013 Alistair Broomhead

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

import sqlite3
import logging
from os import path
from collections import OrderedDict

# from collections import defaultdict
from contextlib import contextmanager

# from abc import ABCMeta
from abc import abstractproperty

# from abc import abstractmethod

from datetime import datetime as dt

# identity = lambda x: x


def identity(x):
    """identity function"""
    return x


class SQLBase:
    db = path.join(path.expanduser("~"), "python-logging-proxy.sqlite")
    sql_schema = abstractproperty(lambda _: "")
    sql_insert = abstractproperty(lambda _: "")
    _flds = abstractproperty(lambda _: {})

    @property
    def as_row(self):
        return tuple(func(getattr(self, key)) for (key, func) in self._flds.items())

    def _process_init_kwargs(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __init__(self, **kwargs):
        self._process_init_kwargs(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

    @staticmethod
    def _identifying_data():
        return ""

    def __repr__(self):
        return "<%(class_name)s%(ident)s at %(hex_id)s>" % {
            "class_name": type(self).__name__,
            "hex_id": hex(id(self)),
            "ident": self._identifying_data(),
        }

    @classmethod
    @contextmanager
    def _conn_db(cls, db=None):
        db = db if db is not None else cls.db
        with sqlite3.connect(db, timeout=20) as conn:
            try:
                while True:
                    try:
                        conn.cursor().execute(
                            "CREATE TABLE IF NOT EXISTS lock ("
                            "locked INTEGER NOT NULL, "
                            "CHECK (locked IN (1)));"
                        )
                        conn.cursor().execute(
                            "CREATE UNIQUE INDEX IF NOT EXISTS "
                            "unique_lock ON lock (locked);"
                        )
                        conn.cursor().execute("INSERT INTO lock VALUES (1)")
                        break
                    except conn.OperationalError:
                        pass
                    # except sqlite3.IntegrityError:
                    # pass
                yield conn
            finally:
                conn.cursor().execute("DELETE FROM lock")

    @classmethod
    def init_table(cls, db=None):
        with cls._conn_db(db) as conn:
            conn.execute(cls.sql_schema)

    def insert(self, db=None):
        try:
            with self._conn_db(db) as conn:
                conn.execute(self.sql_insert, self.as_row)
        except sqlite3.IntegrityError:
            self._logger.error(
                "This log entry does not seem unique: {}".format(self.as_row)
            )


def _SQLiteRecord_fields():
    sql_schema = """CREATE TABLE IF NOT EXISTS log(
                        Created float PRIMARY KEY,
                        Name text,
                        LogLevel int,
                        LogLevelName text,
                        Message text,
                        Args text,
                        Module text,
                        FuncName text,
                        LineNo int,
                        Exception text,
                        Process int,
                        Thread text,
                        ThreadName text
                   )"""
    sql_insert = """INSERT INTO log( Created, Name,
                                    LogLevel, LogLevelName, Message, Args,
                                    Module, FuncName, LineNo, Exception,
                                    Process, Thread, ThreadName )
                   VALUES (         ?, ?,
                                    ?, ?, ?, ?,
                                    ?, ?, ?, ?,
                                    ?, ?, ? ); """
    _flds = OrderedDict(
        [
            ("created", identity),
            ("name", identity),
            # ('host_name', identity),
            # ('port', identity),
            ("log_level", identity),
            ("log_level_name", identity),
            ("message", identity),
            ("args", repr),
            ("module", identity),
            ("func_name", identity),
            ("line_no", identity),
            ("exception", identity),
            ("process", identity),
            ("thread", identity),
            ("threadName", identity),
        ]
    )
    return sql_schema, sql_insert, _flds


class SQLiteRecord(SQLBase):
    sql_schema, sql_insert, _flds = _SQLiteRecord_fields()
    seen_entries = OrderedDict()

    def _identifying_data(self):
        return " for %(path)s at %(created)r =: %(response)r" % {
            "path": self.args["request"]["path"].split("?")[0],
            "created": self.created,
            "response": self.args["response"]["data"],
        }

    def __init__(
        self,
        created,
        name,
        log_level,
        log_level_name,
        message,
        args,
        module,
        func_name,
        line_no,
        exception,
        process,
        thread,
        threadName,
    ):
        super(SQLiteRecord, self).__init__(
            created=created,
            name=name,
            # host_name=host_name,
            # port=port,
            log_level=log_level,
            log_level_name=log_level_name,
            message=message,
            args=args,
            module=module,
            func_name=func_name,
            line_no=line_no,
            exception=exception,
            process=process,
            thread=thread,
            threadName=threadName,
        )
        if isinstance(self.args, str):
            self.args = eval(self.args)

    # noinspection PyPropertyDefinition
    @classmethod
    def last_seen(cls, recheck=False, db=None):
        if recheck:
            for _ in cls.get_unseen(db):
                pass
        key = next(reversed(cls.seen_entries))
        return cls.seen_entries[key]

    @classmethod
    def _see(cls, data):
        if data[0] not in cls.seen_entries:
            cls.seen_entries[data[0]] = SQLiteRecord(*data)
        return cls.seen_entries[data[0]]

    @classmethod
    def get_entry(cls, created, db=None):
        with cls._conn_db(db) as conn:
            curs = conn.cursor()
            curs.execute("SELECT * FROM log WHERE Created=?", (created,))
            data = curs.fetchone()
        yield cls._see(data)

    @classmethod
    def get_all(cls, db=None):
        unseen = cls.get_unseen(db)
        for k in cls.seen_entries:
            yield cls.seen_entries[k]
        for entry in unseen:
            yield entry

    @classmethod
    def get_unseen(cls, db=None):
        created = cls.last_seen().created if cls.seen_entries else 0
        with cls._conn_db(db) as conn:
            curs = conn.cursor()
            for row in curs.execute("SELECT * FROM log WHERE Created>?", (created,)):
                yield cls._see(row)

    @property
    def summary(self):
        req = self.args["request"]
        res = self.args["response"]
        return {
            "name": req["path"],
            "size": len(res["data"]),
            "start_time": req["time"],
            "end_time": res["time"],
            "time_taken": res["time"] - req["time"],
        }


class SQLiteHandler(logging.Handler):
    """
    Logging handler for SQLite.
    Based on Vinay Sajip's DBHandler class
    (http://www.red-dove.com/python_logging.html)
    This version sacrifices performance for thread-safety:
    Instead of using a persistent cursor, we open/close connections for each
    entry.
    AFAIK this is necessary in multi-threaded applications,
    because SQLite doesn't allow access to objects across threads.
    """

    def __init__(self, db=SQLBase.db):

        logging.Handler.__init__(self)
        self.db = db
        # Create table if needed:
        SQLiteRecord.init_table(db)
        # HttpSession.init_table(db)

    def emit(self, record):
        # Use default formatting:
        if record.exc_info:
            record.exc_text = logging._defaultFormatter.formatException(record.exc_info)
        else:
            record.exc_text = ""
        self.format(record)
        try:
            record.asctime
        except AttributeError:
            # record.asctime = record.created
            record.asctime = dt.fromtimestamp(record.created).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )

        # Insert log record:
        SQLiteRecord(
            record.asctime,
            # record.asctime,
            # record.created,
            record.name,
            # record.args['request']['hostname'],
            # record.args['request']['port'],
            record.levelno,
            record.levelname,
            record.message,
            record.args,
            record.module,
            record.funcName,
            record.lineno,
            record.exc_text,
            record.process,
            record.thread,
            record.threadName,
        ).insert(self.db)
