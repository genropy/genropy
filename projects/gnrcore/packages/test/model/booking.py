class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('booking', pkey='id', name_long='Booking',
                        name_plural='Bookings', caption_field='guest_name',
                        rowcaption='$guest_name - $room_type ($check_in)')
        self.sysFields(tbl)
        # Step 1: soggiorno
        tbl.column('check_in', dtype='D', name_long='Check-in')
        tbl.column('check_out', dtype='D', name_long='Check-out')
        tbl.column('room_type', name_long='Room Type')
        tbl.column('num_guests', dtype='L', name_long='Guests',validate_notnul=True,validate_min=1,default=1)
        # Step 2: ospite
        tbl.column('guest_name', name_long='Guest Name')
        tbl.column('guest_email', name_long='Email')
        tbl.column('guest_phone', name_long='Phone')
        tbl.column('document_type', name_long='Document Type')
        tbl.column('document_number', name_long='Document Number')
        # Step 3: servizi
        tbl.column('breakfast', dtype='B', name_long='Breakfast')
        tbl.column('parking', dtype='B', name_long='Parking')
        tbl.column('spa', dtype='B', name_long='Spa')
        tbl.column('notes', name_long='Notes')
        # Step 4: pagamento
        tbl.column('payment_method', name_long='Payment Method')
        tbl.column('card_holder', name_long='Card Holder')
        tbl.column('total_amount', dtype='N', name_long='Total Amount')
        tbl.column('other_guests',dtype='X',name_long='Other guests')
