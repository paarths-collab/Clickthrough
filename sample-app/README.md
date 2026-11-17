# Tasklet

A small task tracker. Node 22.13+ only, no dependencies to install.

    npm run seed     # create the database with demo data (also resets it)
    npm start        # http://localhost:4173
    npm test         # unit tests

Demo logins (password `password123` for all):
`alice@example.com` (has projects and tasks), `bob@example.com` (one
project), `carol@example.com` (nothing yet).

Set `PORT` to change the port. The database is `tasklet.db` in this folder.
