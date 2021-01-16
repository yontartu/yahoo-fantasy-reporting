#!/bin/sh

# Decrypt the file
mkdir $HOME/secrets
# --batch to prevent interactive command
# --yes to assume "yes" for questions
gpg --quiet --batch --yes --decrypt --passphrase="$YAHOO_CRED_PHRASE" --output $HOME/secrets/yahoo_creds.json yahoo_creds.json.gpg