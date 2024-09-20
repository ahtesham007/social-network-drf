# social-network-drf

## Features Implemented

- Users are able to login with their email and password(email is case
insensitive)
- User is able to signup with their email only
- Except signup and login every api can be called by authenticated users only

- API to search other users by email and name(paginate up to 10 records per page).
    - If search keyword matches exact email then only api return user associated with the email.
    - If the search keyword contains any part of the name then it return a list of all users.
    - There will be only one search keyword that will search either by name or email.
- API to send/accept/reject friend request
- API to list friends(list of users who have accepted friend request)
- List pending friend requests(received friend request)
- Users can not send more than 3 friend requests within a minute.

## Additional Features
- Implemented token-based authentication (JWT) with token refreshing capabilities.

- Implemented rate limiting to prevent brute-force attacks on login endpoints

- Implemented role-based access control (RBAC) to restrict access to certain
endpoints user functionality
    - Viewer (can read)
    - Editor (can read, write)
    - Admin (can read, write and delete)

- Ensured the search is optimized for large datasets.

- Ensured atomic operations to handle race conditions when sending or accepting
friend requests.

- If a user rejects a friend request, the sender cannot send another request for a
configurable cooldown period (e.g., 24 hours).

- Implement caching for frequent queries for friend list endpoint.

- Added a feature to block/unblock users, which prevents sending friend requests or
viewing profiles.

- Pagination and sorting options added for Pending Friend Requests.

- Ensured that sensitive information about the requester is not exposed until the
request is accepted.



## Features Beyond Requirements
- Logging
- Unit Tests
- Security

## Pre-Requisite
- Python
- MySQL Server 

## Normal Installation Steps
1. Clone this repository
2. Move inside the social-network-drf directory & create a virtual environment.
3. Create a .env file & update these env variables:
    ```bash
    DB_NAME= 
    DB_USER=
    DB_PASSWORD=
    DB_HOST=
    DB_PORT=
    SECRET_KEY=
4. Install the required packages by running `pip install -r requirements.txt`
5. Run `python manage.py migrate` to create the database tables
6. Run `python manage.py runserver` to start the development server


## Docker Installation Steps
1. Clone this repository
2. Move inside the social-network-drf directory
3. Create a .env file & update these env variables:
Make sure to use root as MySQL User (Might face connection issue)
    ```bash
    # MySQL Database variables
    MYSQL_ROOT_PASSWORD=
    MYSQL_DATABASE=
    MYSQL_USER=
    MYSQL_PASSWORD=

    # Django environment variables
    SECRET_KEY=
    DB_HOST=db
    DB_PORT=3306
    DB_NAME=${MYSQL_DATABASE}
    DB_USER=${MYSQL_USER}
    DB_PASSWORD=${MYSQL_PASSWORD}

4. `docker-compose up --build -d` 

## Run Test
-  `python manage.py test` [Normal Scenario]
-  `docker-compose exec web python manage.py test` [Setup with Docker]

## API Endpoints
- POST /api/v1/signup/
- POST /api/v1/login/
- GET /api/v1/user/?search=ba
- GET /api/v1/friend-requests/
- GET /api/v1/friends/
- POST /api/v1/friend-requests/
- PATCH /api/v1/friend-request-action/2/