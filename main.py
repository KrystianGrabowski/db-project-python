import psycopg2
import json
#from Crypto.Cipher import AES
import argparse
import re

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
        self.conn = psycopg2.connect("dbname={} user={} password={} host=localhost".format(database_name, user_name,
                                                                                password))
        self.cur = self.conn.cursor()
        self.conn.commit()

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

    def function_interpreter(self, name, args):
        data = [[ 1, 0, 2],
           [ 2, 1, 0],
           [ 3, 0, 0]]
        error_occured = False
        try:
            if name == 'open':
                self.connect_to_database(args['database'], args['login'], args['password'])
                if self.user_has_privileges("initialization"):
                    self.database_initialization("db_init.sql")
                self.conn.commit()

            elif name == 'leader':
                pass

            elif name == 'protest':
                pass

            elif name == 'support':
                pass

            elif name == 'upvote':
                pass

            elif name == 'downvote':
                pass

            elif name == 'actions':
                pass

            elif name == 'projects':
                pass

            elif name == 'votes':
                pass

            elif name == 'trolls':
                pass
            
        except Exception:
            error_occured = True
        print(self.status(error_occured, data))
    
    def start_stream(self):
        print("Type '\q' to quit")
        command = ""
        while(True):
            command = input(">>> ")
            if (command == "\q"):
                break
            self.interpret_string_as_json(command)
    
    def status(self, error_occured, data):
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
    if (args.filename != None):
        db.read_from_file(args.filename[0])
        db.cur.close()
        db.conn.close()
    else:
        db.start_stream()

    print("Endofstream")


if __name__ == "__main__":
    main()


