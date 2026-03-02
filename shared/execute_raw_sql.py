import os

from django.db import connection


class ExecuteRawSQL:
    def __init__(self, directory, list=[]):
        self.directory = directory
        self.list = list

    def execute_sql(self, sql):
        c = connection.cursor()
        try:
            c.execute(sql)
        except Exception as e:
            raise e

    def load_sql(self, *args, **kwargs):
        print("\n")
        print("Loading SQL files...")

        # Go through all sql files inside and execute them
        if os.path.exists(self.directory):
            # Get specific SQL files from ordered list
            if len(self.list):
                for filename in self.list:
                    file = filename + '.sql'
                    file_path = os.path.join(self.directory, file)

                    if os.path.exists(file_path):
                        sql_statement = open(file_path).read()
                        self.execute_sql(sql_statement)
                        print("\r")
                        print("Executed file: ", file)
                    else:
                        print("\r")
                        print("Skipping file not found: ", file)

            # Or get all SQL files inside the folder ordered alphabetically:
            else:
                for file in sorted(os.listdir(self.directory)):
                    if file.endswith(".sql"):
                        file_path = os.path.join(self.directory, file)
                        sql_statement = open(file_path).read()
                        self.execute_sql(sql_statement)
                        print("\r")
                        print("Executed file: ", file)
        else:
            print("\r")
            print("Directory not found: ", self.directory)
