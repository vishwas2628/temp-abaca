import threading

from django.db import connection

# Create global lock
thread_lock = threading.RLock()


class ThreadSafeSingleton(object):
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                ThreadSafeSingleton, cls).__new__(cls)
        return cls._instances[cls]


class ExecuteSQLInThread(ThreadSafeSingleton):
    threads = []
    index = 0

    def __init__(self, sql, callback=None):
        thread = {
            'sql': sql,
            'callback': callback,
            'instance': threading.Thread(target=self.run),
            'started': False,
        }
        self.threads.append(thread)

    def execute_sql(self):
        current_thread = self.threads[self.index]

        with connection.cursor() as cursor:
            try:
                cursor.execute(current_thread['sql'])
            except Exception as e:
                raise e
            finally:
                cursor.close()
                print("\r")
                print("Finished thread: ", current_thread['instance'].name)
                print("\r")
                self.index += 1

                # Run callback
                if current_thread['callback'] is not None:
                    current_thread['callback']()
                return

    def start(self):
        for thread in self.threads:
            if not thread['started']:
                thread['instance'].start()
                thread['started'] = True

    def run(self):
        global thread_lock

        with thread_lock:
            print("\r")
            print("Started thread: ",
                  self.threads[self.index]['instance'].name)
            print("\r")
            with thread_lock:
                self.execute_sql()
