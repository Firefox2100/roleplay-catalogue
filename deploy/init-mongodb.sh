#!/bin/sh
set -eu

# Reached via mongodb's own loopback (see `network_mode: service:mongodb` on the
# mongodb-init service in compose.yaml), which is required below for MongoDB's
# localhost exception to apply once authorization is enabled.
mongosh --host 127.0.0.1 --quiet --eval '
  try {
    rs.status().ok
  } catch (error) {
    rs.initiate({_id: "rs0", members: [{_id: 0, host: "mongodb:27017"}]}).ok
  }
'

until mongosh --host 127.0.0.1 --quiet --eval 'quit(db.hello().isWritablePrimary ? 0 : 1)'; do
  sleep 1
done

# Creating this first user permanently closes MongoDB's localhost exception for the
# lifetime of the data directory, so every admin action below authenticates
# explicitly as this user instead of relying on that exception again.
mongosh --host 127.0.0.1 --quiet --eval '
  const admin = db.getSiblingDB("admin");
  if (!admin.getUser(process.env.MONGODB_ROOT_USERNAME)) {
    admin.createUser({
      user: process.env.MONGODB_ROOT_USERNAME,
      pwd: process.env.MONGODB_ROOT_PASSWORD,
      roles: [{role: "root", db: "admin"}],
    });
  }
'

mongosh --host 127.0.0.1 --quiet --eval '
  db.getSiblingDB("admin").auth(process.env.MONGODB_ROOT_USERNAME, process.env.MONGODB_ROOT_PASSWORD);
  const admin = db.getSiblingDB("admin");
  if (!admin.getUser("mongotUser")) {
    admin.createUser({
      user: "mongotUser",
      pwd: process.env.MONGOT_PASSWORD,
      roles: [{role: "searchCoordinator", db: "admin"}],
    });
  } else {
    admin.updateUser("mongotUser", {
      pwd: process.env.MONGOT_PASSWORD,
      roles: [{role: "searchCoordinator", db: "admin"}],
    });
  }
'

# The application connects with its own database-scoped user when one is configured;
# RC_MONGODB_USERNAME is unset (rather than blank) to skip provisioning it and run the
# application without authentication instead.
if [ -n "${RC_MONGODB_USERNAME:-}" ]; then
  mongosh --host 127.0.0.1 --quiet --eval '
    db.getSiblingDB("admin").auth(process.env.MONGODB_ROOT_USERNAME, process.env.MONGODB_ROOT_PASSWORD);
    const appDb = db.getSiblingDB(process.env.RC_MONGODB_NAME);
    if (!appDb.getUser(process.env.RC_MONGODB_USERNAME)) {
      appDb.createUser({
        user: process.env.RC_MONGODB_USERNAME,
        pwd: process.env.RC_MONGODB_PASSWORD,
        roles: [{role: "readWrite", db: process.env.RC_MONGODB_NAME}],
      });
    } else {
      appDb.updateUser(process.env.RC_MONGODB_USERNAME, {
        pwd: process.env.RC_MONGODB_PASSWORD,
        roles: [{role: "readWrite", db: process.env.RC_MONGODB_NAME}],
      });
    }
  '
fi
