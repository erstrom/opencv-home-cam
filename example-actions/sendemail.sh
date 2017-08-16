#! /bin/sh
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
Action detector: $DETECTOR
Action trigger: $TRIGGER
EOF

if [ ! -z ${IMAGE_PATH+x} ] && [ "$IMAGE_PATH" != "No image" ]; then
	# We should attach a jpg image with the email
	if [ ! -f $IMAGE_PATH ] ; then
		echo "$IMAGE_PATH does not exist!"
		exit 1
	fi
	ATTACHMENT="-a $IMAGE_PATH"

	echo "" >> $TEMP_EMAIL_NAME
	echo "The frame that caused this email to be generated has been added as an attachment." >> $TEMP_EMAIL_NAME
	echo "Attachment: $IMAGE_PATH" >> $TEMP_EMAIL_NAME
fi

echo "Sending email. From $FROM_ADDR, to: $TO_ADDR"

sendemail \
    -f $FROM_ADDR \
    -u "opencv-home-cam detection" \
    -t $TO_ADDR \
    -s $SMTP_SERVER \
    -o tls=yes \
    -xu $FROM_ADDR \
    -xp $SMTP_PASSWD \
    -o message-file=$TEMP_EMAIL_NAME \
    $ATTACHMENT

# Remove the temporary email content file
rm $TEMP_EMAIL_NAME
