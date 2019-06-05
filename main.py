import psycopg2
import json
#from Crypto.Cipher import AES
import argparse

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


    def open_database(self, database_name, user_name, password):
        self.conn = psycopg2.connect("dbname={} user={} password={} host=localhost".format(database_name, user_name,
                                                                                password))
        self.cur = self.conn.cursor()
        self.read_from_file_sql("db_init.sql")
        self.conn.commit()
    
    def read_from_file_sql(self, file_name):
        f = open(file_name, 'r')
        self.cur.execute(f.read())
    
    def interpret_string_as_json(self, string):
        f_dict = json.loads(string)
        key = next(iter(f_dict))
        self.function_interpreter(key, f_dict[key])

    def read_from_file(self, file_name):
        f = open(file_name, 'r')
        for line in f:
            self.interpret_string_as_json(line)
        f.close()

    def function_interpreter(self, name, args):
        if name == 'open':
            print("open function")
            self.open_database(args['database'], args['login'], args['password'])

        elif name == 'leader':
            print("leader function")

        elif name == 'protest':
            print("protest function")

        elif name == 'support':
            print("support function")

        elif name == 'upvote':
            print("upvote function")

        elif name == 'downvote':
            print("downvote function")

        elif name == 'actions':
            print("actions function")

        elif name == 'projects':
            print("projects function")

        elif name == 'votes':
            print("votes function")

        elif name == 'trolls':
            print("trolls function")
    
    def start_stream(self):
        pass



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


