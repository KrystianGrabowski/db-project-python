import psycopg2
import json
from Crypto.Cipher import AES
import argparse
import sys

class Database:
    def __init__(self, db_init, debug_mode):
        self.__privilege_level = 0
        self.__db_init = db_init
        self.__debug_mode = debug_mode

    @property
    def privilege_level(self):
        return self.__privilege_level
    
    @privilege_level.setter
    def privilege_level(self, level):
        if 0 <= level <= 2:
            self.__privilege_level = level
        else:
            self.__privilege_level = 0

    def connect_to_database(self, database_name, user_name, password):
        self.conn = psycopg2.connect(dbname=database_name, user=user_name, password=password, host="localhost")
        self.cur = self.conn.cursor()

    def database_initialization(self, file_name):
        self.read_from_file_sql(file_name)
    
    def read_from_file_sql(self, file_name):
        f = open(file_name, 'r')
        self.cur.execute(f.read())
        self.conn.commit()
    
    def interpret_string_as_json(self, string):
        f_dict = json.loads(string)
        key = next(iter(f_dict))
        self.function_interpreter(key, f_dict[key])

    def read_from_file(self, file_name):
        f = open(file_name, 'r')
        for line in f:
            self.interpret_string_as_json(line)
        f.close()

    def user_has_privileges(self, function_name):
        app_user_privileges = []
        print(self.privilege_level)
        if self.privilege_level == 0:
            if function_name in app_user_privileges:
                return True
            return False
        return True
    
    def user_set_privilege_level(self, name):
        self.privilege_level = 1 if name == 'testuser' else 0


    def insert_user(self, id, password, last_activity, leader):
        self.cur.execute("""INSERT INTO member(id, password, last_activity, leader) 
                            VALUES(%s, crypt(%s, gen_salt('md5')), to_timestamp(%s), %s )""", (id, password, last_activity, leader));

    def check_password(self, id, password):
        user_tuple = self.get_user_by_id(id)
        if user_tuple is not None:
            return True if self.compare_passwords(password, user_tuple[1]) else False
        return None

    def get_user_by_id(self, id):
        self.cur.execute("SELECT * FROM member m WHERE m.id = %s;", (id,))
        return self.cur.fetchone()
    
    def compare_passwords(self, password, db_password):
        self.cur.execute("SELECT crypt(%s, %s) = %s;", (password, db_password, db_password))
        return self.cur.fetchone()[0]

    def update_user_timestamp(self, id, password, last_activity):
        self.cur.execute("SELECT * FROM member WHERE id=%s", (id,))
        user_tuple = self.cur.fetchone()
        if user_tuple is not None:
            if self.compare_passwords(password, user_tuple[1]):
                self.cur.execute("UPDATE member SET last_activity=to_timestamp(%s) where id=%s", (last_activity, id))
            else:
                raise Exception('Wrong password')
        else:
            self.insert_user(id, password, last_activity, 'false')


       
    # Funcje API _START_

    def open_function(self, args):
        self.connect_to_database(args['database'], args['login'], args['password'])
        self.user_set_privilege_level(args['login'])
        if self.__db_init and self.user_has_privileges('initialization'):
            self.database_initialization("db_init.sql")

    def leader_function(self, args):
        self.insert_user(args['member'], str(args['password']), args['timestamp'], 'true')
    
    #TO DO
    def protest_function(self, args):
        self.update_user_timestamp(args['member'], args['password'], args['timestamp'])

    def support_function(self, args):
        pass
    
    def upvote_function(self, args):
        pass

    def downvote_function(self, args):
        pass

    def actions_function(self, args):
        pass

    def projects_function(self, args):
        pass
    
    def votes_function(self, args):
        pass

    def trolls_function(self, args):
        pass

    # funkcje API _END_

    def function_interpreter(self, name, args):
        data = None
        error_occured = False
        try:
            (lambda function_name : {
                "open" : lambda args : self.open_function(args),
                "leader" : lambda args : self.leader_function(args),
                "protest" : lambda args : self.protest_function(args),
                "support" : lambda args : self.support_function(args),
                "upvote" : lambda args : self.upvote_function(args),
                "downvote" : lambda args : self.downvote_function(args),
                "actions" : lambda args : self.actions_function(args),
                "projects" : lambda args : self.projects_function(args),
                "votes" : lambda args : self.votes_function(args),
                "trolls" : lambda args : self.trolls_function(args)}[function_name]
            )(name)(args)
        except Exception as e:
            if self.__debug_mode:
                if hasattr(e, 'message'):
                    print(e.message)
                else:
                    print(e)
            error_occured = True
        print(self.status(error_occured, data))

    
    def start_stream(self):
        while 1:
            try: 
                line = sys.stdin.readline()
                if not line:
                    break
                self.interpret_string_as_json(line)
            except KeyboardInterrupt:
                break


    def status(self, error_occured, data):
        if not error_occured:
            try:
                self.conn.commit()
            except Exception as e:
                error_occured = True

        if error_occured:
            return json.dumps({'status': 'ERROR'})
        else:
            if data is None:
                return json.dumps({'status': 'OK'})
            else:
                return json.dumps({'status': 'OK', 'data': data})



def main():
    parser = argparse.ArgumentParser(description='Projekt: System Zarządzania Partią Polityczną')
    parser.add_argument("-i","--init", help="initialization of database", action="store_true")
    parser.add_argument("-g","--debug", help="show information about errors", action="store_true")
    parser.add_argument("-f", "--filename", nargs=1, help="name of the file with JSON objects", type=str)
    args = parser.parse_args()
    db = Database(args.init, args.debug)
    if (args.filename is not None):
        db.read_from_file(args.filename[0])
    else:
        db.start_stream()

    print(db.check_password(1, "abc" ))
    print(db.check_password(1, "acb" ))
    print(db.check_password(2, "aaa" ))
    print(db.check_password(2, "asd" ))
        
    db.cur.close()
    db.conn.close()

    print("END")


if __name__ == "__main__":
    main()


