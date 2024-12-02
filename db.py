import pandas as pd
import psycopg2
import datetime
import traceback
from psycopg2 import sql


class Execute:
    def __init__(self):
        self.keepalive_kwargs = {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 5,
            "keepalives_count": 5,
        }
        self.conn = self.connect()

    def connect(self):
        conn = psycopg2.connect(
            database="central_database",
            user="postgres",
            password="55555",
            host="127.0.0.1",
            port="5432",
            **self.keepalive_kwargs,
        )
        conn.autocommit = True
        return conn

    def insert(self, query, params=None):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            cur.close()
            return True
        except Exception as e:
            print(str(e))
            return False

    def insert_return_id(self, query, params=None):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            id = cur.fetchone()[0]
            cur.close()
            return id
        except Exception as e:
            print(str(e))
            return False

    def select(self, query, params=None):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            rows = [
                dict((cur.description[i][0], value) for i, value in enumerate(row))
                for row in cur.fetchall()
            ]
            cur.close()
            return rows
        except Exception as e:
            print(str(e))
            return False

    def update(self, query, params=None):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            cur.close()
            return True
        except Exception as e:
            print(str(e))
            return False

    def delete(self, query, params=None):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            cur.close()
            return True
        except Exception as e:
            print(str(e))
            return False
    
    
class DB:
    def __init__(self) -> None:
        self.execute = Execute()

    def get_roll_id(self, start_date, end_date):
        try:
            query = sql.SQL("""
                SELECT roll_id, roll_name, roll_number 
                FROM public.roll_details 
                WHERE (roll_end_date >= %s::timestamp AND roll_end_date < %s::timestamp) 
                   OR (roll_start_date >= %s::timestamp AND roll_start_date < %s::timestamp) 
                   AND roll_sts_id = 1 
                ORDER BY roll_id ASC;
            """)
            data = self.execute.select(query, (start_date, end_date, start_date, end_date))
            return data
        except Exception as e:
            print(f"Error fetching roll details: {e}")
            traceback.print_exc()

    def get_needle_line_defects(self, roll_id, defecttyp_id):
        try:
            query = sql.SQL("""
                SELECT alarm_id, defect_details.defect_id, defect_details.timestamp, cam_id, filename, 
                       defect_details.file_path, revolution, angle, coordinate, score 
                FROM public.combined_alarm_defect_details 
                INNER JOIN public.defect_details 
                ON public.defect_details.defect_id = public.combined_alarm_defect_details.defect_id
                WHERE defect_details.roll_id = %s AND defecttyp_id = %s;
            """)
            rows = self.execute.select(query, (roll_id, defecttyp_id))
            return rows
        except Exception as e:
            print(f"Error fetching defect details: {e}")
            traceback.print_exc()

    def get_data_frame(self, date):
        try:
            start_date = date + " 00:00:00"
            end_date = (datetime.datetime.strptime(date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d") + " 00:00:00"
            
            roll_id = self.get_roll_id(start_date, end_date)
            print(roll_id)
            return roll_id
        except Exception as e:
            print(f"Error fetching data frame: {e}")
            traceback.print_exc()

    def get_mills(self):
        """
        Fetches the list of mills from the database.
        Returns: A list of dictionaries containing mill details.
        """
        try:
            query = sql.SQL("""
                SELECT milldetails_id, mill_name 
                FROM public.mill_details 
                ORDER BY milldetails_id ASC;
            """)
            data = self.execute.select(query)
            return data
        except Exception as e:
            print(f"Error fetching mill details: {e}")
            traceback.print_exc()
            return []

    def get_machines_by_mill(self, milldetails_id):
        """
        Fetches the list of machines for a specific mill from the database.
        Args:
            milldetails_id (int): The ID of the mill.
        Returns: A list of dictionaries containing machine details.
        """
        try:
            query = sql.SQL("""
                SELECT machinedetail_id, machine_name 
                FROM public.machine_details 
                WHERE milldetails_id = %s
                ORDER BY machinedetail_id ASC;
            """)
            data = self.execute.select(query, (milldetails_id,))
            return data
        except Exception as e:
            print(f"Error fetching machine details: {e}")
            traceback.print_exc()
            return []
