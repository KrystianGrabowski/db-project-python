import psycopg2
import json
#from Crypto.Cipher import AES
import argparse

class Database:
    def open_database(self):
        conn = psycopg2.connect("dbname=test")
    
    def read_from_file(self, file_name):
        self.f = open(file_name, 'r')
        for line in self.f:
            y = json.loads(line)
            print(next(iter(y)))
        self.f.close()

    def function_interpreter(self, name, args):
        if name == 'open':
            print("open function")
        elif name == 'leader':
            print("open function")
            
def main():
    parser = argparse.ArgumentParser(description='Projekt: System Zarządzania Partią Polityczną')
    parser.add_argument("-i","--init", help="initialization of database", action="store_true")
    parser.add_argument("-f", "--filename", nargs=1, help="name of the file with JSON objects", type=str)
    args = parser.parse_args()
    db = Database()
    #db.open_database()
    print(args.filename[0])
    db.read_from_file(args.filename[0])
    db.open_database()


if __name__ == "__main__":
    main()


