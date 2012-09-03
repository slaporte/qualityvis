
var DASH = (function ($) {
    var DASH = {};
    $(document).ready(function() {
        $('#autorefresh').click(function() {
            if ($(this).is(':checked')){
                DASH.start_reload();
            }
            else {
                DASH.stop_reload();
            }
        });
    });


    DASH.ajax_refresh = function ajax_refresh(div_selector, url, repeat_delay) {
        div_selector = div_selector || '#content';
        url = url || document.URL;
        repeat_delay = repeat_delay || null;
        $(div_selector).load(document.URL + ' ' + div_selector, function() {
            if (repeat_delay) {
                if ($('#autorefresh').is(':checked')){
                    DASH['reload'] = setTimeout(function() { ajax_refresh(div_selector, url, repeat_delay); }, repeat_delay);
                } else {
                    // hmmm, sometimes it doesn't respond to my click... this should stop it
                    clearTimeout(DASH['reload']);
                }
            }
        });
    };

    DASH.get_refresher = function get_refresher(div_selector, url, repeat_delay) {
        var do_refresh = function do_refresh() {
            return ajax_refresh(div_selector, url, repeat_delay);
        };
    };

    DASH.stop_reload = function stop_reload() {
        clearTimeout(DASH['reload']);
    };

    DASH.start_reload = function start_reload(rate) {
        var rate = rate || 221;
        DASH.ajax_refresh('', '', rate);
    };
    return DASH;
}(jQuery));

