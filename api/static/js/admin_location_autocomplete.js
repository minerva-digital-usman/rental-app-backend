$(document).ready(function () {
    const locationInput = $('#id_location');
    const latInput = $('#id_latitude');
    const lonInput = $('#id_longitude');

    const suggestionBox = $('<ul id="address-suggestions" style="position:absolute; z-index:9999; background:white; border:1px solid #ccc; max-height:200px; overflow-y:auto; width:100%; list-style:none; padding:0; margin:0;"></ul>');
    locationInput.after(suggestionBox);
    suggestionBox.hide();

    let typingTimer;
    const delay = 400;

    locationInput.on('input', function () {
        clearTimeout(typingTimer);
        const query = $(this).val();
        typingTimer = setTimeout(() => {
            if (query.length > 2) {
                fetchSuggestions(query);
            } else {
                suggestionBox.empty().hide();
            }
        }, delay);
    });

    function fetchSuggestions(query) {
        $.get(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&addressdetails=1`, function (data) {
            suggestionBox.empty();
            if (data.length === 0) {
                suggestionBox.hide();
                return;
            }

            data.slice(0, 5).forEach(item => {
                const address = item.display_name;
                const houseNumber = item.address ? item.address.house_number : '';
                const fullAddress = houseNumber ? `${address}, ${houseNumber}` : address;

                const option = $('<li></li>')
                    .text(fullAddress)
                    .css({
                        padding: '8px',
                        cursor: 'pointer'
                    })
                    .on('click', function () {
                        locationInput.val(fullAddress);
                        latInput.val(item.lat);
                        lonInput.val(item.lon);
                        suggestionBox.empty().hide();
                    });

                option.hover(
                    () => option.css('background', '#f0f0f0'),
                    () => option.css('background', '#fff')
                );

                suggestionBox.append(option);
            });

            suggestionBox.show();
        });
    }

    // Hide suggestions if clicking outside
    $(document).on('click', function (e) {
        if (!$(e.target).closest('#id_location, #address-suggestions').length) {
            suggestionBox.empty().hide();
        }
    });
});
