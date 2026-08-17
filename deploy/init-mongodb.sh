#!/bin/sh
set -eu

mongosh --host mongodb --quiet --eval '
  try {
    rs.status().ok
  } catch (error) {
    rs.initiate({_id: "rs0", members: [{_id: 0, host: "mongodb:27017"}]}).ok
  }
'

until mongosh --host mongodb --quiet --eval 'quit(db.hello().isWritablePrimary ? 0 : 1)'; do
  sleep 1
done

mongosh --host mongodb --quiet --eval '
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
