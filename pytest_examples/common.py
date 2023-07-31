from pydal import DAL

db = DAL("sqlite://actual.db", migrate=True)
