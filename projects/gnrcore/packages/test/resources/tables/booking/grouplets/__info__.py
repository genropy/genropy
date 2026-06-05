class GroupletTopic(object):
    def __info__(self):
        return dict(
            caption='Booking',
            summary_template="""
                <div>
                    <h3>Booking Confirmation</h3>
                    <div><strong>Guest:</strong> $guest_name</div>
                    <div><strong>Email:</strong> $guest_email</div>
                    <div><strong>Room:</strong> $room_type</div>
                    <div><strong>Check-in:</strong> $check_in</div>
                    <div><strong>Check-out:</strong> $check_out</div>
                    <div><strong>Guests:</strong> $num_guests</div>
                    <hr/>
                    <div><strong>Payment:</strong> $payment_method</div>
                    <div><strong>Total:</strong> $total_amount</div>
                </div>
            """
        )
