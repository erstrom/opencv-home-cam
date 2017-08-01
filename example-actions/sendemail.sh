#! /bin/bash
#
# Example action script for sending email notifications of detections
# using the sendemail tool.

# Your "from-address":
FROM_ADDR="your.from.addr@gmail.com"
# Where do you want the mail to be sent:
TO_ADDR="destination@somewhere.com"
# SMTP server. Below is the gmail SMTP server. If you use gmail you can
# keep this value as is.
SMTP_SERVER="smtp.gmail.com:587"
# SMTP password. This is your (gmail?) password in cleartext.
# It is recomended to use a dedicated email account for the outgoing mails,
# so don't use your "ordinary" email account here!
SMTP_PASSWD="your-cleartext-password"

# Generate email content.
TEMP_EMAIL_NAME=`mktemp`

cat << EOF > $TEMP_EMAIL_NAME
Detection data:

Action timestamp raw: $TIME_STAMP_RAW
Action timestamp: $TIME_STAMP_DATE
Action cascade: $CASCADE
Action trigger: $TRIGGER
EOF

echo "Sending email. From $FROM_ADDR, to: $TO_ADDR"

sendemail \
    -f $FROM_ADDR \
    -u "opencv-home-cam detection" \
    -t $TO_ADDR \
    -s $SMTP_SERVER \
    -o tls=yes \
    -xu $FROM_ADDR \
    -xp $SMTP_PASSWD \
    -o message-file=$TEMP_EMAIL_NAME

# Remove the temporary email content file
rm $TEMP_EMAIL_NAME
