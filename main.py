import psycopg2
import json
#from Crypto.Cipher import AES
import argparse

class Database:
    def open_database(self):
        self.conn = psycopg2.connect("dbname=test user=krystian password=password")
        self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE tabeleczka (id integer, val varchar);")
        self.conn.commit()
    
    def read_from_file(self, file_name):
        self.f = open(file_name, 'r')
        for line in self.f:
            f_dict = json.loads(line)
            key = next(iter(f_dict))
            self.function_interpreter(key, f_dict[key])
        self.f.close()

    def function_interpreter(self, name, args):
        if name == 'open':
            print("open function")

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

def main():
    parser = argparse.ArgumentParser(description='Projekt: System Zarządzania Partią Polityczną')
    parser.add_argument("-i","--init", help="initialization of database", action="store_true")
    parser.add_argument("-f", "--filename", nargs=1, help="name of the file with JSON objects", type=str)
    args = parser.parse_args()
    db = Database()
    print(args.filename[0])
    db.read_from_file(args.filename[0])
    db.open_database()


if __name__ == "__main__":
    main()


