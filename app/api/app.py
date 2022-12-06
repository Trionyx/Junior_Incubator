from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:nWRbi0HR0xYSXQxW60tH@containers-us-west-91.railway.app:7328/railway'
db = SQLAlchemy(app)

# for DB table creation in db_create.py
context = app.app_context()


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())

    def __repr__(self):
        return f'Event: {self.description}'

    def __init__(self, description):
        self.description = description


def format_event(event):
    return {
        "description": event.description,
        "id": event.id,
        "created_at": event.created_at,
    }


@app.route('/')
def hello():
    return 'Hey!'


# create an event
@app.route('/events', methods=['POST'])
def create_event():
    description = request.json['description']
    event = Event(description)
    db.session.add(event)
    db.session.commit()
    return format_event(event)


# get all events
@app.route('/events', methods=['GET'])
def get_events():
    events = Event.query.order_by(Event.id.asc()).all()
    event_list = []
    for event in events:
        event_list.append(format_event(event))
    return {'events': event_list}


# get single event
@app.route('/events/<event_id>', methods=['GET'])
def get_event(event_id):  # event_id here == id from tutorial  # TODO remove comment here at the end
    event = Event.query.filter_by(event_id=event_id).one()
    formatted_event = format_event(event)
    return {'event': formatted_event}


# delete an event
@app.route('/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    event = Event.query.filter_by(id=event_id).one()
    db.session.delete(event)
    db.session.commit()
    return f'Event (event_id: {event_id}) deleted '


# edit an event
@app.route('/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    event = Event.query.filter_by(id=event_id)
    description = request.json['description']
    event.update(dict(description=description, created_at=datetime.utcnow()))
    db.session.commit()
    return {'event': format_event(event.one())}


if __name__ == '__main__':
    app.run()