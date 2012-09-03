
var DASH = (function ($) {
    var DASH = {};
    $(document).ready(function() {
        $('body h1:first').after('<input id="autorefresh" name="autorefresh" type="checkbox" /><label for="autorefresh">Auto-update</label>');
    });


    DASH.ajax_refresh = function ajax_refresh(div_selector, url, repeat_delay) {
        div_selector = div_selector || '#content';
        url = url || document.URL;
        repeat_delay = repeat_delay || null;
        $.ajax({
            url: document.URL,
            type: 'GET',
            data: {ajax: 'true'},
            success: function(data) {
                $(div_selector).replaceWith(data);
                if (repeat_delay) {
                    setTimeout(function() { ajax_refresh(div_selector, url, repeat_delay); }, repeat_delay);
                }
            }
        });
    };

    DASH.get_refresher = function get_refresher(div_selector, url, repeat_delay) {
        var do_refresh = function do_refresh() {
            return ajax_refresh(div_selector, url, repeat_delay);
        };
    };
    return DASH;
}(jQuery));

