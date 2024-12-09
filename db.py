import psycopg2
import traceback
from psycopg2 import sql
from datetime import datetime, timezone, timedelta


class Execute:
    def __init__(self, db_name="central_database", user="postgres", password="55555", host="127.0.0.1", port="5432"):
        self.db_name = db_name
        self.keepalive_kwargs = {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 5,
            "keepalives_count": 5,
        }
        self.conn = self.connect(user=user, password=password, host=host, port=port)

    def connect(self, user, password, host, port):
        """Establish connection to the PostgreSQL database."""
        try:
            conn = psycopg2.connect(
                database=self.db_name,
                user=user,
                password=password,
                host=host,
                port=port,
                **self.keepalive_kwargs,
            )
            conn.autocommit = True
            print(f"Connected to database: {self.db_name}")
            return conn
        except Exception as e:
            print(f"Error connecting to database {self.db_name}: {e}")
            traceback.print_exc()
            raise

    def select(self, query, params=None):
        """Execute a SELECT query and return the results."""
        try:
            cur = self.conn.cursor()
            print(f"Executing SELECT query: {query} with params: {params}")
            cur.execute(query, params)
            rows = [
                dict((cur.description[i][0], value) for i, value in enumerate(row))
                for row in cur.fetchall()
            ]
            cur.close()
            print(f"SELECT query executed successfully, fetched {len(rows)} rows.")
            return rows
        except Exception as e:
            print(f"Error executing SELECT query: {e}")
            traceback.print_exc()
            return []

    def execute_query(self, query, params=None):
        """Execute a query (INSERT/UPDATE/DELETE) and return the results."""
        try:
            cur = self.conn.cursor()
            print(f"Executing query: {query} with params: {params}")
            cur.execute(query, params)
            results = cur.fetchall()
            cur.close()
            print(f"Query executed successfully, fetched {len(results)} rows.")
            return results
        except Exception as e:
            print(f"Error executing query: {e}")
            traceback.print_exc()
            return []

    def close(self):
        """Close the database connection."""
        try:
            self.conn.close()
            print("Database connection closed.")
        except Exception as e:
            print(f"Error closing database connection: {e}")
            traceback.print_exc()


class DB:
    def __init__(self):
        """Initialize connections to both central and knitting databases."""
        print("Initializing database connections...")
        self.central_execute = Execute(
            db_name="central_database",
            user="postgres",
            password="55555",
            host="127.0.0.1",
            port="5432",
        )
        self.knitting_execute = Execute(
            db_name="knitting",
            user="postgres",
            password="55555",
            host="127.0.0.1",
            port="5432",
        )

    def get_mills(self):
        """Fetch list of mills from the central database."""
        try:
            query = sql.SQL("""
                SELECT milldetails_id, mill_name 
                FROM public.mill_details 
                ORDER BY milldetails_id ASC;
            """)
            print(f"Fetching mills from central database...")
            data = self.central_execute.select(query)
            if not data:
                print("No mills found.")
            else:
                print(f"Found {len(data)} mills.")
            return data
        except Exception as e:
            print(f"Error fetching mill details: {e}")
            traceback.print_exc()
            return []

    def get_machines_by_mill(self, milldetails_id):
        """Fetch machines for a specific mill from the central database."""
        try:
            query = sql.SQL("""
                SELECT machinedetail_id, machine_name 
                FROM public.machine_details 
                WHERE milldetails_id=%s
                ORDER BY machinedetail_id ASC;
            """)
            print(f"Fetching machines for mill ID {milldetails_id}...")
            data = self.central_execute.select(query, (milldetails_id,))
            if not data:
                print(f"No machines found for mill ID: {milldetails_id}")
            else:
                print(f"Found {len(data)} machines for mill ID {milldetails_id}.")
            return data
        except Exception as e:
            print(f"Error fetching machine details for mill ID {milldetails_id}: {e}")
            traceback.print_exc()
            return []
    def get_mill_machine_by_ip(self,mill_ip):
        try:
            query  = ""
        except Exception as e:
            print("Error in get_mill_machine_by_ip:", str(e))
            traceback.print_exc()
            return None

    def get_data_frame(self, date):
        """Fetch roll IDs based on the calculated start and end date."""
        try:
            print(f"Fetching data for date: {date}...")
            # Convert the input date string to a datetime object
            localized_date = datetime.strptime(date, "%Y-%m-%d")
            
            # Calculate the start and end dates for the 24-hour period, ensuring they are timezone-aware
            start_date = localized_date.replace(hour=0, minute=0, second=0, microsecond=0)
            # Assuming the system is using Kolkata time zone (UTC+5:30)
            start_date = start_date.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            end_date = start_date + timedelta(days=1)  # Move to the next day at midnight

            print(f"Start Date: {start_date}, End Date: {end_date}")
            roll_ids = self.get_roll_id(start_date, end_date)
            print(f"Roll IDs found: {roll_ids}")
            return roll_ids
        except Exception as e:
            print("Error in get_data_frame:", str(e))
            traceback.print_exc()
            return []

    def get_machine_ip(self, mill_id, machine_id):
        """Fetch the machine's IP address based on mill ID and machine ID."""
        try:
            query = sql.SQL("""
                SELECT ip_address 
                FROM public.machine_details 
                WHERE milldetails_id=%s AND machinedetail_id=%s;
            """)
            print(f"Fetching machine IP for Mill ID {mill_id} and Machine ID {machine_id}...")
            result = self.central_execute.select(query, (mill_id, machine_id))
            if result:
                print(f"Machine IP: {result[0]['ip_address']}")
                return result[0]['ip_address']
            else:
                print(f"No IP address found for Mill ID {mill_id} and Machine ID {machine_id}.")
                return None
        except Exception as e:
            print(f"Error fetching machine IP address: {e}")
            traceback.print_exc()
            return None

    def get_roll_id(self, start_date, end_date):
        """Fetch roll IDs for a 24-hour period."""
        try:
            query = """
                SELECT roll_id, roll_name 
                FROM roll_details 
                WHERE timestamp >= %s AND timestamp < %s;
            """
            print(f"Fetching roll IDs between {start_date} and {end_date}...")
            results = self.knitting_execute.execute_query(query, (start_date, end_date))
            print(f"Roll IDs retrieved: {results}")
            return results
        except Exception as e:
            print(f"Error in get_roll_id: {e}")
            traceback.print_exc()
            return []

    def get_needle_line_defects(self, roll_id, defecttyp_id):
        """Fetch needle line defects based on roll ID and defect type."""
        try:
            query = """
                SELECT alarm_id, defect_details.defect_id, defect_details.timestamp, cam_id, filename, 
                       defect_details.file_path, revolution, angle, coordinate, score 
                FROM public.combined_alarm_defect_details 
                INNER JOIN public.defect_details 
                ON public.defect_details.defect_id = public.combined_alarm_defect_details.defect_id
                WHERE defect_details.roll_id = %s AND defecttyp_id = %s;
            """
            print(f"Fetching defects for roll ID {roll_id} and defect type ID {defecttyp_id}...")
            rows = self.knitting_execute.execute_query(query, (roll_id, defecttyp_id))
            print(f"Defects retrieved: {rows}")
            return rows
        except Exception as e:
            print(f"Error fetching needle line defects: {e}")
            traceback.print_exc()
            return []

    def close_connections(self):
        """Close database connections."""
        try:
            self.central_execute.close()
            self.knitting_execute.close()
            print("Database connections closed successfully.")
        except Exception as e:
            print(f"Error closing database connections: {e}")
            traceback.print_exc()
