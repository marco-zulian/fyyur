#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import json
import dateutil.parser
import datetime
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

venues_genres = db.Table(
   'Venue_Genres',
    db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True),
)

artists_genres = db.Table(
   'Artist_Genres',
   db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True),
   db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True),
)

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    genres = db.relationship('Genre', secondary=venues_genres, backref=db.backref('venues', lazy=True))
    seeking_talent = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String)
    shows = db.relationship('Show', backref=db.backref('venue', lazy=True), cascade='all, delete-orphan')

    def as_dict(self):
      return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    genres = db.relationship('Genre', secondary=artists_genres, backref=db.backref('artists', lazy=True))
    seeking_venue = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String)
    shows = db.relationship('Show', backref=db.backref('artist', lazy=True), cascade='all, delete-orphan')

    def as_dict(self):
      return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Show(db.Model):
   __tablename__ = 'Show'

   id = db.Column(db.Integer, primary_key=True)
   artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
   venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
   start_time = db.Column(db.DateTime, nullable=False)

class Genre(db.Model):
   __tablename__ = 'Genre'

   id = db.Column(db.Integer, primary_key=True)
   name = db.Column(db.String, nullable=False)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  if isinstance(value, str):
    date = dateutil.parser.parse(value)
  else:
    date = value

  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#  Venues
#  ----------------------------------------------------------------
def getVenueUpcomingShows(venue_id):
  return db.session.query(Show.start_time, Artist.id, Artist.name, Artist.image_link) \
    .join(Artist, Artist.id == Show.artist_id) \
    .filter(Show.start_time > datetime.now(), Show.venue_id == venue_id) \
    .all()

def getVenuePastShows(venue_id):
  return db.session.query(Show.start_time, Artist.id, Artist.name, Artist.image_link) \
    .join(Artist, Artist.id == Show.artist_id) \
    .filter(Show.start_time < datetime.now(), Show.venue_id == venue_id) \
    .all()

@app.route('/venues')
def venues():
  data = []
  cities = db.session.query(Venue.city, Venue.state).distinct().all()

  for city in cities:
    venues = db.session \
      .query(Venue.id, Venue.name) \
      .where(Venue.city == city[0]) \
      .where(Venue.state == city[1]) \
      .all()

    data.append({
      "city": city[0],
      "state": city[1],
      "venues": [{
        "id": venue[0],
        "name": venue[1],
        "num_upcoming_shows": len(getVenueUpcomingShows(venue[0]))
      } for venue in venues]
    })

  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term=request.form.get('search_term', '')
  query = db.session.query(Venue.id, Venue.name).filter(Venue.name.icontains(search_term))

  response={
    "count": query.count(),
    "data": [{
      "id": venue[0],
      "name": venue[1],
      "num_upcoming_shows": len(getVenueUpcomingShows(venue[0]))
    } for venue in query.all()]
  }

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = db.session.get(Venue, venue_id)

  pastShows = getVenuePastShows(venue.id)
  upcomingShows = getVenueUpcomingShows(venue.id)

  data = venue.as_dict()
  data["genres"] = [genre.name for genre in venue.genres]
  data["past_shows"] = [{"artist_id": show[1],
                         "artist_name": show[2],
                         "artist_image_link": show[3],
                         "start_time": show[0]} for show in pastShows]
  data["past_shows_count"] = len(pastShows)
  data["upcoming_shows"] = [{"artist_id": show[1],
                             "artist_name": show[2],
                             "artist_image_link": show[3],
                             "start_time": show[0]} for show in upcomingShows]
  data["upcoming_shows_count"] = len(upcomingShows)

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False

  try:
    venue = Venue(
      name=request.form['name'],
      city=request.form.get('city', type=str),
      state=request.form.get('state', type=str),
      address=request.form.get('address', type=str),
      phone=request.form.get('phone', type=str),
      image_link=request.form.get('image_link', type=str),
      facebook_link=request.form.get('facebook_link', type=str),
      website=request.form.get('website_link', type=str),
      genres = [Genre.query.filter_by(name=genre).one() for genre in request.form.getlist('genres')],
      seeking_talent='seeking_talent' in request.form.keys(),
      seeking_description=request.form.get('seeking_description', type=str)
    )

    db.session.add(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  else:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  error = False

  try:
    venue = Venue.query.get(venue_id)
    db.session.delete(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    abort(500)
  else:
    return jsonify({
      "success": True,
      "status": 200,
    })

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data=[{
    "id": artist.id,
    "name": artist.name,
  } for artist in db.session.query(Artist).all()]

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term=request.form.get('search_term', '')
  query = db.session.query(Artist).filter(Artist.name.icontains(search_term))

  response={
    "count": query.count(),
    "data": [{
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": len(artist.shows),
    } for artist in query.all()]
  }

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.get(artist_id)

  upcomingShows = [show for show in artist.shows if show.start_time > datetime.now()]
  pastShows = [show for show in artist.shows if show.start_time < datetime.now()]
  
  data = artist.as_dict()
  data['genres'] = [genre.name for genre in artist.genres]

  data['past_shows'] = [{
    "venue_id": show.venue.id,
    "venue_name": show.venue.name,
    "venue_image_link": show.venue.image_link,
    "start_time": show.start_time
  } for show in pastShows]
  data['past_shows_count'] = len(pastShows)

  data['upcoming_shows'] = [{
    'venue_id': show.venue.id,
    'venue_name': show.venue.name,
    'venue_image_link': show.venue.image_link,
    'start_time': show.start_time
  } for show in upcomingShows]
  data['upcoming_shows_count'] = len(upcomingShows)

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)

  artist_dict = artist.as_dict()
  artist_dict['website_link'] = artist.website
  artist_dict['genres'] = [genre.name for genre in artist.genres]

  form = ArtistForm(**artist_dict)

  return render_template('forms/edit_artist.html', form=form, artist=artist_dict)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  error = False

  try:
    artist = Artist.query.get(artist_id)

    with db.session.no_autoflush:
      for field, value in request.form.items():
        try:
          setattr(artist, field, value)
        except:
          pass
      
      artist.genres = [Genre.query.filter_by(name=genre).one() for genre in request.form.getlist('genres')]
      artist.website = request.form['website_link']
      artist.seeking_venue = 'seeking_venue' in request.form.keys()

    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    abort(500)
  else:
    return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)

  venue_dict = venue.as_dict()
  venue_dict['website_link'] = venue.website
  venue_dict['genres'] = [genre.name for genre in venue.genres]

  form = VenueForm(**venue_dict)

  return render_template('forms/edit_venue.html', form=form, venue=venue_dict)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  error = False

  try:
    venue = Venue.query.get(venue_id)

    with db.session.no_autoflush:
      for field, value in request.form.items():
        try:
          setattr(venue, field, value)
        except:
          pass
      
      venue.genres = [Genre.query.filter_by(name=genre).one() for genre in request.form.getlist('genres')]
      venue.website = request.form['website_link']
      venue.seeking_talent = 'seeking_talent' in request.form.keys()

    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    abort(500)
  else:
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error = False
  
  try:
    artist = Artist(
      name=request.form['name'],
      city=request.form.get('city', type=str),
      state=request.form.get('state', type=str),
      phone=request.form.get('phone', type=str),
      image_link=request.form.get('image_link', type=str),
      facebook_link=request.form.get('facebook_link', type=str),
      website=request.form.get('website_link', type=str),
      genres = [Genre.query.filter_by(name=genre).one() for genre in request.form.getlist('genres')],
      seeking_venue='seeking_venue' in request.form.keys(),
      seeking_description=request.form.get('seeking_description', type=str)
    )

    db.session.add(artist)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
  else:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  
  return render_template('pages/home.html')

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = db.session \
    .query(Show.start_time, Venue.id, Venue.name, Artist.id, Artist.name, Artist.image_link) \
    .join(Venue, Venue.id == Show.venue_id) \
    .join(Artist, Artist.id == Show.artist_id) \
    .all()
  
  data=[{
    "venue_id": show[1],
    "venue_name": show[2],
    "artist_id": show[3],
    "artist_name": show[4],
    "artist_image_link": show[5],
    "start_time": show[0]
  } for show in shows]

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error = False

  try:
    show = Show(artist_id=request.form['artist_id'],
                venue_id=request.form['venue_id'],
                start_time=request.form['start_time'])
    db.session.add(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Show could not be listed.')
  else:
    flash('Show was successfully listed!')
  
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
