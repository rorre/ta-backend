# Tutor Angkatan Back-end

Back-end for Tutor Angkatan CSUI 2021. [Front-end repository is available here](https://github.com/rorre/ta-frontend).

Tutor Angkatan is a service that is available for CSUI 2021 to help one another in academics. It does so by letting other people to create an open course and schedule a Meet/Zoom call.

Back-end uses Python(>=3.8), Postgres, and FastAPI.

## Developing

### Requirements

-   Python >=3.8
-   Poetry
-   SQLite/Postgres/MySQL\*
-   Redis (Rate limiting)

**NOTE**: Currently, MySQL connector is not included in dependencies. Please install it manually.

### Installing

-   Install the project

```
$ poetry install
```

-   Create an empty .env file with the following structure

```
database_url=
redis_url=
secret=
hostname=
```

-   Run a database migration

```
$ alembic upgrade head
```

### Running

Simply run `uvicorn ta_backend:app.app`. More information is provided in [Uvicorn's documentation](https://www.uvicorn.org/).

## Contributing

See [CONTRIBUTING](CONTRIBUTING.md).
