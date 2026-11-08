from planner.database import test_connection

try:
    test_connection()

    print("SUCCESS: Supabase connected!")
    print("SUCCESS: trip_plans table accessible!")

except Exception as e:
    print("ERROR: Supabase connection failed!")
    print(e)