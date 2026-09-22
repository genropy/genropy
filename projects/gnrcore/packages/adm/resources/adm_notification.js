/* The dialog a user is shown for a pending adm.user_notification.

   It lives here, and no longer inside frameindex.js where it was born,
   because the notification form lets an administrator open the very same
   dialog on any of its recipients: a preview built by imitating this one
   would stop being the notification the user sees the first time the two
   drift apart. */
var notificationDialog = {

    /* Build the dialog for one adm.user_notification row.

       `preview` builds it for somebody who is not its recipient. The buttons
       are drawn exactly as the user gets them -- what they say, and whether
       the cancel one exists at all, is the part being previewed -- but
       neither of them acts: confirming does not mark the row as confirmed,
       refusing does not log the administrator out. Both just close it, and
       the dialog gets a close box of its own, since a mandatory notification
       leaves the user no way out by design. */
    open: function(notification_id, preview) {
        var datapath = preview ? 'notification_preview' : 'notification';
        genro.setData(datapath + '.confirm', null);
        var notification_data = genro.serverCall('_table.adm.user_notification.getNotification', {pkey:notification_id});
        var dlg = genro.dlg.quickDialog(notification_data['title'], {_showParent:true, max_width:'900px',
                                                                    datapath:datapath, background:'white',
                                                                    closable:preview ? true : null});
        var box = dlg.center._('div', {overflow:'auto', height:'500px', padding:'10px'});
        box._('div', {innerHTML:notification_data.notification, border:'1px solid transparent', padding:'10px'});
        var cancel_label = notification_data.cancel_button_label;
        var slots = cancel_label ? ['cancel', '*'] : ['*'];
        if (notification_data.confirm_label) {
            slots.push('confirm_checkbox', '2');
        }
        slots.push('confirm');
        var bar = dlg.bottom._('slotBar', {slots:slots.join(','), height:'22px'});
        if (cancel_label) {
            // Refusing the notification leaves nowhere to go but the logout, so the
            // button asks before doing it. A notification with no cancel label has no
            // button at all, and confirming is then the only way into the application.
            bar._('button', 'cancel', {'label':_T(cancel_label, true), command:'cancel', action:function() {
                genro.dlg.ask(_T('!!Warning'),
                              '!!If you do not confirm you will be logged out of the application',
                              null, {confirm:function() {
                                  if (preview) {
                                      dlg.close_action();
                                  } else {
                                      genro.logout();
                                  }
                              }});
            }});
        }
        if (notification_data.confirm_label) {
            bar._('checkbox', 'confirm_checkbox', {value:'^.confirm', label:_T(notification_data.confirm_label, true)});
        }
        bar._('button', 'confirm', {'label':_T(notification_data.confirm_button_label || '!!Confirm', true),
                                    command:'confirm',
                                    disabled:notification_data.confirm_label ? '^.confirm?=!#v' : null,
                                    action:function() {
            if (preview) {
                dlg.close_action();
                return;
            }
            genro.serverCall('_table.adm.user_notification.confirmNotification', {pkey:notification_id},
                             function(n_id) {
                                 dlg.close_action();
                                 if (n_id) {
                                     notificationDialog.open(n_id);
                                 } else {
                                     genro.publish('end_notification');
                                 }
                             });
        }});
        dlg.show_action();
    }
};
