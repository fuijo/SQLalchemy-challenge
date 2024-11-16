from flask import Flask, jsonify
import numpy as np
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
import datetime as dt

# Initialize the Flask app
app = Flask(__name__)

# Database setup
engine = create_engine("sqlite:///Resources/hawaii.sqlite")
Base = automap_base()
Base.prepare(engine, reflect=True)

# Reflect the tables
Measurement = Base.classes.measurement
Station = Base.classes.station

# Helper function to calculate the date one year ago from the most recent date
def date_prev_year():
    session = Session(engine)
    most_recent_date = session.query(func.max(Measurement.date)).scalar()
    prev_year_date = dt.datetime.strptime(most_recent_date, "%Y-%m-%d") - dt.timedelta(days=365)
    session.close()
    return prev_year_date.strftime("%Y-%m-%d")

# Homepage route
@app.route("/")
def homepage():
    return """
    <h1>Welcome to the Honolulu, Hawaii Climate API!</h1>
    <h3>Available Routes:</h3>
    <ul>
        <li><a href="/api/v1.0/precipitation">/api/v1.0/precipitation</a> - Last 12 months of precipitation data</li>
        <li><a href="/api/v1.0/stations">/api/v1.0/stations</a> - List of weather stations</li>
        <li><a href="/api/v1.0/tobs">/api/v1.0/tobs</a> - Temperature observations of the most active station for the last 12 months</li>
        <li><a href="/api/v1.0/2017-01-01">/api/v1.0/2017-01-01</a> - Minimum, average, and maximum temperatures from a start date (format: yyyy-mm-dd)</li>
        <li><a href="/api/v1.0/2017-01-01/2017-12-31">/api/v1.0/2017-01-01/2017-12-31</a> - Minimum, average, and maximum temperatures for a date range (format: yyyy-mm-dd)</li>
    </ul>
    """

# Precipitation route
@app.route("/api/v1.0/precipitation")
def precipitation():
    session = Session(engine)
    prev_year = date_prev_year()
    precipitation_data = session.query(Measurement.date, Measurement.prcp).filter(Measurement.date >= prev_year).all()
    session.close()

    # Convert to dictionary
    precipitation_dict = {date: prcp for date, prcp in precipitation_data}
    return jsonify(precipitation_dict)

# Stations route
@app.route("/api/v1.0/stations")
def stations():
    session = Session(engine)
    station_data = session.query(Station.station, Station.name).all()
    session.close()

    # Convert to list of dictionaries
    station_list = [{"station": station, "name": name} for station, name in station_data]
    return jsonify(station_list)

# Temperature observations (TOBS) route
@app.route("/api/v1.0/tobs")
def tobs():
    session = Session(engine)
    prev_year = date_prev_year()

    # Query the most active station
    most_active_station = session.query(Measurement.station).group_by(Measurement.station).\
        order_by(func.count(Measurement.id).desc()).first()[0]

    # Query TOBS for the most active station
    tobs_data = session.query(Measurement.date, Measurement.tobs).\
        filter(Measurement.station == most_active_station).\
        filter(Measurement.date >= prev_year).all()
    session.close()

    # Convert to list of dictionaries
    tobs_list = [{"date": date, "tobs": tobs} for date, tobs in tobs_data]
    return jsonify(tobs_list)

# Start date route
@app.route('/api/v1.0/<start>', methods=['GET'])
def start_date(start):
    try:
        # Debugging: print the start date to ensure it's passed correctly
        print(f"Received start date: {start}")

        # Validate the date format (YYYY-MM-DD)
        dt.datetime.strptime(start, '%Y-%m-%d')

        # Create a session
        session = Session(engine)

        # Query TMIN, TAVG, TMAX for dates >= start
        results = session.query(
            func.min(Measurement.tobs),
            func.avg(Measurement.tobs),
            func.max(Measurement.tobs)
        ).filter(Measurement.date >= start).all()

        # Close the session
        session.close()

        # If no results, return an error message
        if not results or results[0][0] is None:
            return jsonify({"error": f"No data found for start date {start}."}), 404

        # Prepare the response
        data = {
            "start_date": start,
            "TMIN": results[0][0],
            "TAVG": results[0][1],
            "TMAX": results[0][2]
        }
        return jsonify(data)

    except ValueError:
        # If the date format is invalid, return an error
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    except Exception as e:
        # Catch other exceptions
        return jsonify({"error": str(e)}), 500

# Start and end date route
@app.route("/api/v1.0/<start>/<end>", methods=['GET'])
def start_end_date(start, end):
    session = Session(engine)
    results = session.query(
        func.min(Measurement.tobs),
        func.avg(Measurement.tobs),
        func.max(Measurement.tobs)
    ).filter(Measurement.date >= start).filter(Measurement.date <= end).all()
    session.close()

    # Prepare and return results
    data = {
        "start_date": start,
        "end_date": end,
        "TMIN": results[0][0],
        "TAVG": results[0][1],
        "TMAX": results[0][2]
    }
    return jsonify(data)

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
