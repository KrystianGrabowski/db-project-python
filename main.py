import psycopg2
import json
from Crypto.Cipher import AES
import argparse
import sys

class Database:
    def __init__(self):
        self.__privilege_level = 0;

    @property
    def privilege_level(self):
        return self.__privilege_level
    
    @privilege_level.setter
    def privilege_level(self, level):
        if 0 <= level:
            self.__privilege_level = level

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
        if self.privilege_level == 0:
            if function_name in app_user_privileges:
                return True
            return False
        return True

    def insert_user(self, id, password, last_activity, leader):
        self.cur.execute("""INSERT INTO member(id, password, last_activity, leader) 
                            VALUES(%s, crypt(%s, gen_salt('md5')), to_timestamp(%s), %s )""", (id, password, last_activity, leader));

    def check_password(self, id, password):
        self.cur.execute("SELECT * FROM member m WHERE m.id = %s AND m.password = crypt(%s, m.password);", (id, password))
        if self.cur.fetchone() is None:
            return False
        else:
            return True


    def open_function(self, args):
        self.connect_to_database(args['database'], args['login'], args['password'])
        if self.user_has_privileges("initialization"):
            self.database_initialization("db_init.sql")

    def leader_function(self, args):
        self.insert_user(args['member'], str(args['password']), args['timestamp'], 'true')
    
    #TO DO
    def protest_function(self, args):
        pass

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
    parser.add_argument("-f", "--filename", nargs=1, help="name of the file with JSON objects", type=str)
    args = parser.parse_args()
    db = Database()
    db.privilege_level = 1 if args.init else 0
    if (args.filename is not None):
        db.read_from_file(args.filename[0])
        db.cur.close()
        db.conn.close()
    else:
        db.start_stream()

    print("END")


if __name__ == "__main__":
    main()


