(function ($) {
    $(document).ready(function () {

        
        function updateTimeslotDropdown() {
            console.log("updateTimeslotDropdown called");
            var courtType = $('#id_court_type').val();
            var date = $('#id_reservation_date').val();
            var level = $('#id_level').val();
            var playerType = $('#id_player_type').val();
            var requestData = {
                'court_type': courtType,
                'date': date
            };

            // Show/hide level and player_type fields based on court_type
            if (courtType === 'individual') {
                $('#id_level').closest('.field-level').show();
                $('#id_player_type').closest('.field-player_type').show();
                $('#id_slot_count').closest('.form-row').show();  // Show slot_count for individual type

                requestData['level'] = level;
                requestData['player_type'] = playerType;
            } else {
                $('#id_level').closest('.field-level').hide();
                $('#id_player_type').closest('.field-player_type').hide();
                $('#id_slot_count').closest('.form-row').hide();  // Hide slot_count for full_court type
            }

            // Store the current selected timeslot ID
            var currentTimeslotId = $('#id_timeslot').val();

            $.ajax({
                url: '/get_timeslots/',
                data: requestData,
                dataType: 'json',
                beforeSend: function () {
                    console.log("Sending AJAX request with data:", requestData);
                },
                success: function (data) {
                    var timeslots = JSON.parse(data.timeslots);
                    console.log("Received timeslots:", timeslots);  // Debugging log
                    var $timeslotSelect = $('#id_timeslot');
                    $timeslotSelect.empty();

                    $.each(timeslots, function (index, timeslot) {
                        // Check if the timeslot is fully booked
                        if (courtType === 'full_court' && timeslot.is_fully_booked) {
                            console.log("Skipping fully booked full court timeslot:", timeslot.pk);
                            return; // Skip this iteration
                        }

                        var optionText = 'Court: ' + timeslot.court_name +
                            ', Start Time: ' + timeslot.start_time +
                            ', End Time: ' + timeslot.end_time +
                            ', Booking Type: ' + timeslot.booking_type;

                        if (timeslot.booking_type === "Individual") {
                            optionText += ', Player Type: ' + timeslot.player_type +
                                ', Level: ' + timeslot.level +
                                ', Available Slots: ' + timeslot.available_slots;
                        }
                        // Debugging: Log the ID and option text to the console
                        console.log("Adding option - ID:", timeslot.pk, ", Text:", optionText);

                        $timeslotSelect.append($('<option></option>').attr('value', timeslot.pk).text(optionText));
                    });

                    // Reset the selected timeslot to the previously selected ID
                    if (currentTimeslotId) {
                        $timeslotSelect.val(currentTimeslotId);
                    }
                }

            });
        }

        $('#id_court_type, #id_reservation_date, #id_level, #id_player_type, #id_slot_count').change(updateTimeslotDropdown);
        // Call the function initially to populate the dropdown
        //updateTimeslotDropdown();

    });
})(jQuery);
