/**
 * Article quality visualization mediawiki gadget
 *  for the San Francisco Mediawiki Hackathon, 2012
 *  for more information, see https://www.mediawiki.org/wiki/January_2012_San_Francisco_Hackathon
 *
 * By: Ben Plowman, Mahmoud Hashemi, Sarah Nahm, and Stephen LaPorte
 *
 * Copyright 2012
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
 
 // TODO: save/replay queue?
 // TODO: report failed inputs on evaluators

var jsdom = require('jsdom');
var dummy_window = jsdom.jsdom().createWindow();
dummy_window.XMLHttpRequest = require('xmlhttprequest').XMLHttpRequest;
var jq_lib = require('jquery');
var $ = jq_lib.create(dummy_window);
    $.support.cors = true;
var extend = $.extend;
var Step = require('./step.js');

// logging setup
var logger, use_devnull;
try {
    var Logger = require('devnull');
    var stream_transport = require('devnull/transports/stream');
    logger = new Logger({namespacing: 0,
                         timestamp: false,});
    logger.warn = logger.warning; //mock console's interface
    use_devnull = true;
} catch (e) {
    console.warn('devnull logger not found, using console for logging.');
    logger = console;
    logger.warning = logger.warn; // mock devnull's interface
    use_devnull = false;
}

// these can be overridden at the command line. node gadget_node.js --help for
// more information
var DEFAULT_ARTICLE_COUNT = 5;
var DEFAULT_CATEGORY      = 'Category:Featured_articles';
var DEFAULT_LOG_FILE      = 'fetch.log';
var GLOBAL_TIMEOUT        = 6000; // milliseconds
var GLOBAL_RETRY_COUNT    = 3;
var EV_CONCURRENCY        = 10;
var QUERY_CONCURRENCY     = 8;
var CAT_CONCURRENCY       = 4;
var OUTPUT_HTML           = false;

var ALL_CATS = Infinity;

// Namespace ID constants
var ARTICLE_NS  = 0;
var TALK_NS     = 1;
var CATEGORY_NS = 14;
var PORTAL_NS   = 100;


function keys(obj) {
    var ret = [];
    for(var k in obj) {
        if (obj.hasOwnProperty(k)) {
            ret.push(k);
        }
    }
    return ret;
}

function values(obj) {
    var ret = [];
    for(var k in obj) {
        if (obj.hasOwnProperty(k)) {
            ret.push(obj[k]);
        }
    }
    return ret;
}

// max, min, mean, variance, std deviation, length
function array_stats(a) {
    var r = {mean: 0, variance: 0, deviation: 0, max: 0, min: Infinity, sum: 0, length: 0};
    var t = r.length = a.length;
    var m, s, l;
    //for(var m, s = 0, l = t; l--; ); // one-line sum
    for(i = 0; i < t; ++i) {
        r.max = a[l] > r.max ? a[l] : r.max;
        r.min = a[l] < r.min ? a[l] : r.min;
        s += a[l];
    }
    r.sum = s;
    
    // sum of individual variances
    for(m = r.mean = s / t, l = t, s = 0; l--; s += Math.pow(a[l] - m, 2));
    r.deviation = Math.sqrt(r.variance = s / t); // set deviation and variance
    return r;
}

// TODO: register/save function?
// TODO: (possibly related to ^) record/replay
var queue = function queue(workers, description, autostart) {
    var self = {};
    queue_desc = description || 'Anonymous queue';
    
    self.desc          = queue_desc;
    self.is_processing = (typeof start === 'undefined') ? true : autostart;
    self.is_closed     = false;
    self.pending       = [];
    self.cur_executing = 0;
    self.max_executing = workers;
    
    self.enqueue = function enqueue(func, callback) {
        if(!self.is_closed) {
            self.pending.push({'func':func, 'callback':callback});
            if(self.is_processing) {
                process();
            }
        }
    };
    self.stop = function stop() {
        self.is_processing = false;
    };
    self.close = function close() {
        self.is_closed = true;
    };
    self.start = function start() {
        self.is_processing = true;
        process();
    };
    self.get_unfinished_count = function get_unfinished_count() {
        return self.pending.length + self.cur_executing;
    };
    
    var get_retry = function get_retry(task) {
        return function task_retry() {
            var item_name = task.func.desc || 'unknown queued function';
            self.cur_executing -= 1;
            self.enqueue(task.func, task.callback);
        };
    };
    var get_callback = function get_callback(task) {
        return function task_callback() {
            self.cur_executing -= 1;
            process();
            try {
                task.callback.apply(this, arguments);
            } catch (exc) {
                var item_name = task.func.desc || 'unknown queued function';
                var callback_name = task.callback.name;
                logger.error(queue_desc + ': Major error when calling queue task ' + item_name + "'s callback '" + callback_name + "'.");
                throw exc;
            }
        };
    };
    var process = function process() {
        var do_nothing = ( (self.cur_executing >= self.max_executing) // full
                         || (self.pending.length <= 0)                // no tasks
                         || (!self.is_processing));                   // stopped/not started
        if (do_nothing) {
            return;
        }
        var n = self.pending.pop();
        
        var callback = get_callback(n);
        var retry = get_retry(n);
        
        self.cur_executing += 1;
        try {
            n.func(callback, retry);
        } catch (exc){
            logger.error(queue_desc + ': Major failure :/ ' + n.desc);
            callback(exc, null);
        }
    };
    return self;
};

var WindowManager = function WindowManager(count, progress, init_callback) {
    var jsdom = require('jsdom');
    var self = {};
    
    self.all_windows = all_windows =  [];
    self.avail_windows = avail_windows = [];
    self.eval_registry = eval_registry = {};
    
    self.window_gets = 0;
  
    self.get_window = function get_window(title) {
        var ret = avail_windows.pop();
        self.window_gets++;
        if (!ret) {
            logger.error('No available windows for "'+title+'"');
            logger.info('Current window holders are: ');
            logger.info(keys(eval_registry));
        } else {
            eval_registry[title] = ret;
        }
        return ret;
    };

    self.release_window = function release_window(window, title) {
        if (window) {
            avail_windows.push(window);
        } else {
            logger.warning(title+" did not return a window.");
        }
        delete eval_registry[title];
        
        return;
    };
  
    for (var i=0; i < count; ++i) {
        jsdom.env({
            html: "<html><body></body></html>",
            done: function(errors, window) {
                jq_lib.create(window);
                all_windows.push(window);
                avail_windows.push(window);
                if (all_windows.length == count) {
                    init_callback();
                }
            }
        });
    }
    return self;
};


var cli = require('cli');
cli.parse({
    article_count:      ['n', 'Number of articles to fetch', 'number', DEFAULT_ARTICLE_COUNT]
    ,category_name:     ['c', 'Category of articles to fetch', 'string', DEFAULT_CATEGORY]
    ,recursive:         ['r', 'Also evaluate subcategories recursively']
    ,evaluator_workers: ['E', 'Number of evaluators to process simultaneously', 'number', EV_CONCURRENCY]
    ,query_workers:     ['Q', 'Number of web queries to fetch simultaneously', 'number', QUERY_CONCURRENCY]
    ,cat_workers:       ['C', 'Number of category member lists to fetch simultaneously', 'number', CAT_CONCURRENCY]
    ,global_timeout:    ['T', 'Amount of time to wait for web queries (in milliseconds)', 'number', GLOBAL_TIMEOUT]
    ,log_file:          ['L', 'Path of file to log to (tail it for old-style output)', 'string', DEFAULT_LOG_FILE]
    ,debug:             ['D', 'TBI: disable progress meters, log to stdout at debug loglevel']
});

var mq, jsdomq, catq, wm, pm;


// Convenience functions for reward formulae
function overStat(threshold, great, reward) {
    return {'type':'over','threshold': threshold, 'great': great,'reward': reward};
}

function underStat(threshold, great, reward) {
    return {'type':'under', 'threshold': threshold, 'great': great, 'reward': reward};
}

function rangeStat(start, end, max_score) {
    return {'type':'range','start':start,'threshold':end,'reward':max_score};
}

/*
 * Metrics for article quality
 */
var rewards = {
    'vetted': {
        'total_editors'        : overStat(20, 40, 200),
        'paragraph_count'       : rangeStat(10, 30, 100),
        'wikitrust'             : underStat(0.6, 0.45, 600)
    },
    // rewards.vetted.['visits_per_last_edit'] = ;
    // rewards.vetted.['flags_total'] = ;
    'structure': {
        'ref_section'           : overStat(1, 1, 100),
        'external_links_total'  : overStat(10, 20, 200)
    },
    // rewards.structure.intro_paragraph = ;
    // rewards.structure.sections_per_link = overStat(;
    'richness': {
        'image_count'           : overStat(5, 7, 300),
        'external_links_total'  : overStat(10, 20, 100)
    },
    // rewards.richness.length = ;
    // rewards.richness.audio = ;
    // rewards.geodata = ;
    'integrated': {
        'category_count'        : overStat(15, 30, 100),
        'incoming_links'        : overStat(3, 50, 100),
        'outgoing_links'        : overStat(3, 50, 100),
        'internal_links'        : overStat(100, 200, 400)
    },
    //rewards.integrated.read_more_section = ;
    'community': {
        'total_editors'        : overStat(20, 40, 100),
        'fbTrustworthy'         : overStat(3, 3.5, 100),
        'fbObjective'           : overStat(3, 3.5, 100),
        'fbComplete'            : overStat(3, 3.5, 100),
        'fbWellwritten'         : overStat(3, 3.5, 100)
    },
    //rewards.community.assessment = ;
    //rewards.community.visits_per_day = ;
    //rewards.community.visits_per_last_edit = ;
    //rewards.community.flags_total = ;
    'citations': {
        'ref_count'             : overStat(100, 300, 100),
        'ref_needed_count'      : underStat(5, 0, 100),
        'pov_statement_count'   : underStat(2, 0, 100)

    },
    //rewards.citations.reference_count_per_paragraph = ;
    //rewards.citations.citation_flag = ;
    'significance': {

    }
    //rewards.significance.paragraph_per_web_results = {};
    //rewrads.significance.paragraph_per_news_results = {};
    //rewards.significance = overStat(;
};

var successful_queries = 0;
var failed_queries = 0;
var complete_queries = 0;

function do_query(url, complete_callback, kwargs) {
    var all_kwargs = {
        url: url,
        type: 'get',
        dataType: 'json',
        timeout: GLOBAL_TIMEOUT, //for detecting jsonp errors
        success: function(data) {
            successful_queries++;
            if (successful_queries % 20 === 0) {
                var util = require('util');
                logger.info(successful_queries + ' successful queries.'+
                    ' (Memory usage: '+process.memoryUsage()['rss']/(1024*1024) + ' MB)');
            }
            complete_callback(null, data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            failed_queries++;
            logger.warning(failed_queries + ' failed queries: ' + url);
            complete_callback(errorThrown, null);
        },
        complete: function(jqXHR, textStatus) {
            // TODO: error handling (jsonp doesn't get error() calls for a lot of errors)
            complete_queries++;
        },
        headers: { 'User-Agent': 'QualityVis/0.0.0 Mahmoud Hashemi makuro@gmail.com' }
    };

    for (var key in kwargs) {
        if(kwargs.hasOwnProperty(key)) {
            all_kwargs[key] = kwargs[key];
        }
    }
    $.ajax(all_kwargs);
}

var web_source = function(url) {
    var self = function fetch_web_source(callback) {
        do_query(url, callback);
    };
    self.get_url = function get_url() {
        return url;
    };
    return self;
};

var yql_source = function(query) {
    return function fetch_yql_source(callback) {
        var kwargs = {data: {q: query, format: 'json'}};
        do_query('http://query.yahooapis.com/v1/public/yql', callback, kwargs);
    };
};

// WIP
var grokse_input = function(context) {
    var self;
    
    self = {
        type: 'Grokse',
        desc: 'Grokse for '+context.article_title,
        fetch: null,
        calculate: null
    };
    return self;
};//input('grokseStats', yql_source('select * from json where url ="http://stats.grok.se/json/en/201201/' + article_title + '"'), grokseStats)


// TODO configurable retry failure. at least retry in a couple seconds.
// complete is called on the input actually completely finishing (success/fatal error)
// ind_complete is called for an individual call's completion (retry)
var input = function input(desc, fetch_or_data, process) {
    var self;

    self = function self(complete, retry) {
        self.desc     = desc;
        self.attempts = self.attempts + 1 || 1;
        var fetch_callback = function fetch_callback(err, data) {
            self.fetch_data = data; //may or may not be large
            if (err || !data) {
                //logger.info('failed fetch on: '+desc+' '+err);
                self.results = null;
                err = err || 'Unknown error';
                self.error = 'Fetch failed on'+self.desc+': '+err;
            } else {
                try {
                    if (process) {
                        self.results = process(data);
                    } else {
                        self.results = data;
                    }
                } catch (proc_err) {
                    self.results = null;
                    self.error = 'Processing failed on '+self.desc+': '+proc_err;
                    //logger.info(self.error);
                }
            }
            if (self.results) {
                try {
                    complete(null, self);
                } catch (myerr) {
                    self.results = null;
                    self.error = 'Exception while completing '+self.desc+', somehow: '+myerr;
                    complete(null, self);
                }
            } else {
                if (self.attempts <= GLOBAL_RETRY_COUNT) {
                    retry();
                } else {
                    self.results = null;
                    if (self.error) {
                        self.error += '('+self.attempts+' attempts)';
                    } else {
                        self.error = self.desc+' encountered unknown error, failed after '+self.attempts+' retries.';
                    }
                    complete(null, self);
                }
            }
        };
        
        if (fetch_or_data instanceof Function) {
            // fetch_or_data is a function to fetch the data
            var fetch = fetch_or_data;
            fetch(fetch_callback);
        } else {
            // fetch_or_data is the data itself
            var data = fetch_or_data;
            fetch_callback(null, data);
        }
    };
    self.attempts = 0;
    
    return self;
};



// Input refactor steps/notes:
// 1. Make specialized inputs with template-like URLs
// 2. All inputs are constructed with a context dictionary or precomputed data as the
//    only argument. The return is a callable object that can be enqueued.
// 3. Make web_input and yql_input contextualize the query (the input constructor passes
//    through the context)
// 4. What goes into a context? Title, Article ID, Rev ID, more? Input-specific stuff?
//    Can it all be determined at input runtime or is there some horrible uninternalized
//    state?
// 5. Have a default list of input constructors for convenience.
var make_evaluator = function(dom, rewards, callback, mq) {

    var self          = {};
    var query_results = [];
    var callbacks     = [callback];
    
    self.article_title = article_title = dom.mw.config.get('wgTitle');
    self.article_id    = article_id    = dom.mw.config.get('wgArticleId');
    self.revision_id   = revision_id   = dom.mw.config.get('wgCurRevisionId');
    self.eval_date     = new Date();
    self.dom           = dom; // TODO rename to document for internal use?
    self.rewards       = rewards;
    
    self.data    = {};
    self.results = null;
    self.failed_inputs = [];
    
    Step(function register_inputs() {
        var results_group = this.group();
        var uri_title = encodeURIComponent(article_title);
        self.inputs  = [
            input('inLinkStats', web_source('http://en.wikipedia.org/w/api.php?action=query&format=json&list=backlinks&bltitle=' + uri_title + '&bllimit=500&blnamespace=0'), inLinkStats)
            ,input('feedbackStats', web_source('http://en.wikipedia.org/w/api.php?action=query&list=articlefeedback&afpageid=' + article_id + '&afuserrating=1&format=json&afanontoken=01234567890123456789012345678912'), feedbackStats)
            ,input('searchStats', web_source('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=' + uri_title), searchStats)
            ,input('newsStats',  web_source('http://ajax.googleapis.com/ajax/services/search/news?v=1.0&q=' + uri_title), newsStats)
            ,input('wikitrustStats', yql_source('select * from html where url ="http://en.collaborativetrust.com/WikiTrust/RemoteAPI?method=quality&revid=' + revision_id + '"'), wikitrustStats)
            ,input('grokseStats', yql_source('select * from json where url ="http://stats.grok.se/json/en/latest90/' + uri_title + '"'), grokseStats)
            ,input('getAssessment', web_source('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=Talk:' + uri_title + '&rvprop=content&redirects=true&format=json'), getAssessment)
            ,input('domStats', dom, domStats)
            //,input('bingWebStats', web_source('http://api.bing.net/json.aspx?Appid=202F17E764089C60340ACA3FBBC558453354DA76&query=' + uri_title  +  '&web.count=1&news.count=1&sources=web+news'), bingWebStats)
            ,input('revisionStats', web_source('http://ortelius.toolserver.org:8088/revisions/' + uri_title), revisionStats)
        ];
        
        for(var i=0; i<self.inputs.length; ++i) {
            mq.enqueue(self.inputs[i], results_group());
        }
        
    }, function calculate_results(err, completed_inputs) {
        if (err) {
            logger.info('One or more inputs failed: ' + err);
            throw err;
        }
        
        var merged_data = {};
        for (var i = 0; i < completed_inputs.length; ++i) {
            var cur_input = completed_inputs[i];
            if (!cur_input.results) {
                var err_str = 'Input failed: '+ cur_input.desc;
                if (cur_input.error && cur_input.attempts) {
                    err_str += ' with error: ' + cur_input.error + ' after ' + cur_input.attempts + ' attempts.';
                }
                self.failed_inputs.push(cur_input);
            } else {
                for (var prop in cur_input.results) {
                    merged_data[prop] = cur_input.results[prop];
                }
            }
        }
        self.data = merged_data;
        self.results = calc_scores(merged_data, rewards);
        
        return self.results;
        
    }, function eval_complete(err, eval_results) {
        if (err) {
            var err_type = typeof(err);
            if (err_type != 'object' && err_type != 'function') {
                err = new Error(err);
            }
            err.dom = self.dom;
            
            for(var i=0; i < callbacks.length; ++i) {
                callbacks[i](err, null); //call all the on_complete callbacks
            }
        } else {
            for(var i=0; i < callbacks.length; ++i) {
                callbacks[i](null, self); //call all the on_complete callbacks
            }
        }
    });
    
    self.to_dict = function to_dict() {
        var ret = { article_title: self.article_title,
                    article_id:    self.article_id,
                    revision_id:   self.revision_id,
		    eval_date:     self.eval_date.toString(),
		  };
        for ( stat in self.data ) {
            ret[stat] = self.data[stat];
        }
        return ret;
    };
    
    self.on_complete = function(callback) {
        callbacks.push(callback);
        // if the queries are complete, we need to manually trigger callback
        if (query_results.length == self.inputs.length && self.results) {
            callback(null, self);
        }
    };

    var calc_scores = function(stats, rewards) {
        var result = {};

        result.recos = {};

        for(var area in rewards) {
            for(var attr in rewards[area]) {
                var r = rewards[area][attr], // reward structure for this area/attr combo

                    s = stats[attr], // page stat for this attribute
                    val = 0;

                if (!r || !s) {
                    continue;
                }

                if(r.type == 'over') {
                    if( s >= r.great ) {
                            val = r.reward;
                    } else if ( s >= r.threshold ) {
                            val = r.reward * 0.7; // TODO: make tuneable?
                    }
                } else if (r.type == 'under') {
                    if( s < r.great ) {
                                val = r.reward;
                    } else if ( s < r.threshold ) {
                                val = r.reward * 0.7; // TODO: make tuneable?
                    }
                } else if (r.type === 'range') {
                    var slope = r.reward / r.start;
                    if( s < r.start) {
                            val = s * slope;
                    } else if( s > r.threshold){
                            val = r.reward - ((s - r.threshold) * slope);
                            val = Math.max(0, val);
                    } else {
                            val = r.reward;
                    }
                }
                if (val < r.reward) {
                    result.recos[attr] = result.recos[attr] || {};

                    var gain = r.reward - val;
                    result.recos[attr].points    = result.recos[attr].points + gain || gain;
                    result.recos[attr].cur_stat  = s;
                }

                result[area]       = result[area] || {};
                result[area].score = result[area].score + val || val;
                result[area].max   = result[area].max + r.reward || r.reward;

                result.total       = result.total || {};
                result.total.score = result.total.score + val || val;
                result.total.max   = result.total.max + r.reward || r.reward;
            }
        }
        return result;
    };
    
    return self;
};

// Start calculation functions

// One limitation on this model (easily refactored): calculators can't read from data
// they can only write to it. Mostly this is because we don't know what will or won't
// be present.

function domStats(dom) {
    var ret = {},
        $   = dom.jQuery;

    function section_stats(header) {
        /* requires jquery */
        var sub_words = [];
        var word_count = 0;
        var len = 0;
        $(header).each(function() {
            if($(this).text() != "Contents") {
                sub_words.push($(this).nextUntil(header).text().split(/\b[\s,\.-:;]*/).length);
            }
        });
        function sortNum(a, b) {
            return b - a;
        }
        for (var n in sub_words) {
            word_count += sub_words[n];
        }
        if(sub_words.length !== 0) {
            var average = word_count / sub_words.length;
            var smallest = sub_words.sort(sortNum).slice(-1)[0];
            var largest = sub_words.sort(sortNum)[0];
            return {'average': average, 'smallest': smallest, 'largest': largest, 'total': sub_words.length};
        } else {
            return {'average': 0, 'smallest': 0, 'largest': 0, 'total': 0};
        }
    }
    
    ret.query_category_count = dom.mw.config.get('wgCategories').length;
    /**
    these are available in the api query, but not the live mw dom object
    
    ret.query_external_links_count = dom.parse.externallinks.length;
    ret.query_images_count  = dom.parse.images.length;
    ret.query_langlinks_count = dom.parse.langlinks.length;
    ret.query_links         = dom.parse.links.length;
    ret.query_sections      = dom.parse.sections.length;
    ret.query_templates     = dom.parse.templates.length; */

    /* structural features */
    h2                      = section_stats('h2');
    ret.h2_average          = h2.average;
    ret.h2_large            = h2.largest;
    ret.h2_small            = h2.smallest;
    ret.h2_total            = h2.total;
    h3                      = section_stats('h3');
    ret.h3_average          = h3.average;
    ret.h3_large            = h3.largest;
    ret.h3_small            = h3.smallest;
    ret.h3_total            = h3.total;
    h4                      = section_stats('h4');
    ret.h4_average          = h4.average;
    ret.h4_large            = h4.largest;
    ret.h4_small            = h4.smallest;
    ret.h4_total            = h4.total;
    h5                      = section_stats('h5');
    ret.h5_average          = h5.average;
    ret.h5_large            = h5.largest;
    ret.h5_small            = h5.smallest;
    ret.h5_total            = h5.total;
    ret.h6_total            = section_stats('h6').total;

    /* general size */
    ret.word_count          = $('p').text().split(/\b[\s,\.-:;]*/).length;
    ret.paragraph_count     = $('p').length;
    ret.paragraph_counts    = [];
    $('p').each(function() {
        ret.paragraph_counts.push($(this).text().split(/\b[\s,\.-:;]*/).length); /* words per paragraph */
    });

    /* reference features */
    ret.ref_count           = $('.reference').length; /* includes both references and notes */
    ret.source_count        = $('li[id^="cite_note"]').length; /* includes both references and notes */
    
    /* section organization */
    ret.reference_section_count = $('#References').length;
    ret.external_links_section_count = $('#External_links').length;
    ret.intro_p_count       =  $('#toc').prevAll('p').length;
    ret.new_internal_link_count = $('.new').length;
    ret.infobox_count       = $('.infobox').length;

    /* in section counts */
    ret.footnotes_in_section = $('#Footnotes').parent().nextAll('div').children('ul').children('li').length;
    ret.external_links_in_section = $('#External_links').parent().nextAll('ul').children().length;
    ret.see_also_links_in_section = $('#See_also').parent().nextAll('ul').children().length;

    /* linkage */
    ret.external_links_total_count = $('.external').length;
    ret.links = [];
    $('p a:not([class])[href^="/wiki/"]').each(function() {
        ret.links.push($(this).text()); /* all the links ... TODO: disamibg */
    });
    ret.links_count         = ret.links.length;
    ret.dom_internal_link_count = $('p a:not([class])[href^="/wiki/"]').length;


    /* flags */
    ret.ref_needed_count    = $('span:contains("citation")').length;
    ret.pov_statement_count = $('span:contains("neutrality")').length;

    /* this will be 0 from api */
    ret.dom_category_count  = $("a[href^='/wiki/Category:']").length;

    /* multimedia */
    ret.image_count         = $('img').length;
    ret.ogg                 = $("a[href$='ogg']").length;
    ret.mid                 = $("a[href$='mid']").length;
    ret.geo                  = $('.geo-dms').length;


    /* templates will (most likely) be 0 or 1 */
    ret.templ_delete        = $('.ambox-delete').length;
    ret.templ_autobiography = $('.ambox-autobiography').length; // Template:Autobiography
    ret.templ_advert        = $('.ambox-Advert').length; // Template:Advert
    ret.templ_citation_style = $('.ambox-citation_style').length; // Template:Citation style
    ret.templ_cleanup       = $('.ambox-Cleanup').length;
    ret.templ_COI           = $('.ambox-COI').length;
    ret.templ_confusing     = $('.ambox-confusing').length;
    ret.templ_context       = $('.ambox-Context').length;
    ret.templ_copy_edit     = $('.ambox-Copy_edit').length;
    ret.templ_dead_end      = $('.ambox-dead_end').length;
    ret.templ_disputed      = $('.ambox-disputed').length;
    ret.templ_essay_like    = $('.ambox-essay-like').length;
    ret.templ_expert        = $("td:contains('needs attention from an expert')").length; // Template:Expert
    ret.templ_fansight      = $('td:contains("fan\'s point of view")').length;
    ret.templ_globalize     = $('td:contains("do not represent a worldwide view")').length;
    ret.templ_hoax          = $('td:contains("hoax")').length;
    ret.templ_in_universe   = $('.ambox-in-universe').length;
    ret.templ_intro_rewrite = $('.ambox-lead_rewrite').length;
    ret.templ_merge         = $('td:contains("suggested that this article or section be merged")').length;
    ret.templ_no_footnotes  = $('.ambox-No_footnotes').length;
    ret.templ_howto         = $('td:contains("contains instructions, advice, or how-to content")').length;
    ret.templ_non_free      = $('.ambox-non-free').length;
    ret.templ_notability    = $('.ambox-Notability').length;
    ret.templ_not_english   = $('.ambox-not_English').length;
    ret.templ_NPOV          = $('.ambox-POV').length;
    ret.templ_original_research = $('.ambox-Original_research').length;
    ret.templ_orphan        = $('.ambox-Orphan').length;
    ret.templ_plot          = $('.ambox-Plot').length;
    ret.templ_primary_sources = $('.ambox-Primary_sources').length;
    ret.templ_prose         = $('.ambox-Prose').length;
    ret.templ_refimprove    = $('.ambox-Refimprove').length;
    ret.templ_sections      = $('.ambox-sections').length;
    ret.templ_tone          = $('.ambox-Tone').length;
    ret.templ_tooshort      = $('.ambox-lead_too_short').length;
    ret.templ_style         = $('.ambox-style').length;
    ret.templ_uncategorized = $('.ambox-uncategorized').length;
    ret.templ_update        = $('.ambox-Update').length;
    ret.templ_wikify        = $('.ambox-Wikify').length;

    /* may return 0+ (more = worse) */
    ret.templ_multiple_issues = $('.ambox-multiple_issues li').length;

    return ret;
}

function bingWebStats(data) {
    ret = {};
    ret.bing_news_results = data.SearchResponse.News.Total;
    ret.bing_web_results = data.SearchResponse.Web.Total;
    return ret;
}

function revisionStats(data) {
    ret = data;

    ret.rev_per_day     = ret.total_revisions / ret.age;
    ret.IP_per_day      = ret.IP_edit_count / ret.age;
    ret.minor_per_day   = ret.minor_count / ret.age;
    ret.revert_per_day  = ret.reverts_estimate / ret.age;

    ret.IP_per_rev      = ret.IP_edit_count / ret.total_revisions;
    ret.minor_per_rev   = ret.minor_count / ret.total_revisions;
    ret.revert_per_rev  = ret.reverts_estimate / ret.total_revisions;
    ret.last_30_per_rev = ret.last_30_days_total_revisions / ret.total_revisions;
    ret.last_500_per_rev = ret.last_500_total_revisions / ret.total_revisions;
    ret.talk_per_rev    = ret.talk_revisions / ret.total_revisions;
    ret.editors_five_plus_per_editor = ret.editors_five_plus_edits / ret.total_editors;

    ret.talkers_per_editors = ret.talk_total_editors / ret.total_editors;

    return data;
}

function inLinkStats(data) {
    //TODO: if there are 500 backlinks, we need to make another query
    var ret = {};
    ret.incoming_links = data.query.backlinks.length;
    return ret;
}
    
function feedbackStats(data) {
    var ret = {};
    
    var ratings     = data.query.articlefeedback[0].ratings;
    if (!ratings) {
        return ret;
    }
    var trustworthy = ratings[0],
        objective   = ratings[1],
        complete    = ratings[2],
        wellwritten = ratings[3];

    ret.fbTrustworthy   = trustworthy.total / trustworthy.count;
    ret.fbObjective     = objective.total / objective.count;
    ret.fbComplete      = complete.total / complete.count;
    ret.fbWellwritten   = wellwritten.total / wellwritten.count;

    return ret;
}

function searchStats(data) {
    var ret = {};
    ret.google_search_results = parseInt(data.responseData.cursor.estimatedResultCount, 10);
    return ret;
}

function newsStats(data) {
    var ret = {};
    ret.google_news_results = parseInt(data.responseData.cursor.estimatedResultCount, 10);
    return ret;
}

function wikitrustStats(data) {
    var ret = {};
    var res = data.query.results.body.p;
    var success = (res.indexOf('EERROR') !== 0);
    if (success) {
        ret.wikitrust = parseFloat(res);
    }
    return ret;
}

function grokseStats(data) {
    var ret = { view_total: 0, view_max: 0, view_min: Infinity };
    data = data.query.results.json;
    var views = values(data['daily_views']);

    for(var i=0; i<views.length; i++) {
        var curview = parseInt(views[i], 10);
        ret.view_total += curview;
        ret.view_max = (curview > ret.view_max) ? curview : ret.view_max;
        ret.view_min = (curview < ret.view_min) ? curview : ret.view_min;
    }
    ret.view_average = ret.view_total / views.length;
    
    return ret;
}

function getAssessment(data) {
    var ret = {};
    var id      = keys(data.query.pages)[0],
        text    = (data.query.pages[id].revisions['0']['*']);

    /* From the 'metadata' gadget
     * @author Outriggr - created the script and used to maintain it
     * @author Pyrospirit - currently maintains and updates the script
     */
    var rating = 'none';
    if (text.match(/\|\s*(class|currentstatus)\s*=\s*fa\b/i))
    rating = 'fa';
    else if (text.match(/\|\s*(class|currentstatus)\s*=\s*fl\b/i))
    rating = 'fl';
    else if (text.match(/\|\s*class\s*=\s*a\b/i)) {
    if (text.match(/\|\s*class\s*=\s*ga\b|\|\s*currentstatus\s*=\s*(ffa\/)?ga\b/i))
            rating = 'a/ga'; // A-class articles that are also GA's
    else rating = 'a';
    } else if (text.match(/\|\s*class\s*=\s*ga\b|\|\s*currentstatus\s*=\s*(ffa\/)?ga\b|\{\{\s*ga\s*\|/i) &&
              !text.match(/\|\s*currentstatus\s*=\s*dga\b/i))

        rating = 'ga';
    else if (text.match(/\|\s*class\s*=\s*b\b/i))
    rating = 'b';
    else if (text.match(/\|\s*class\s*=\s*bplus\b/i))
    rating = 'bplus'; // used by WP Math
    else if (text.match(/\|\s*class\s*=\s*c\b/i))
    rating = 'c';
    else if (text.match(/\|\s*class\s*=\s*start/i))
    rating = 'start';
    else if (text.match(/\|\s*class\s*=\s*stub/i))
    rating = 'stub';
    else if (text.match(/\|\s*class\s*=\s*list/i))
    rating = 'list';
    else if (text.match(/\|\s*class\s*=\s*sl/i))
    rating = 'sl'; // used by WP Plants
    else if (text.match(/\|\s*class\s*=\s*(dab|disambig)/i))
    rating = 'dab';
    else if (text.match(/\|\s*class\s*=\s*cur(rent)?/i))
    rating = 'cur';
    else if (text.match(/\|\s*class\s*=\s*future/i))
    rating = 'future';
    ret.assessment = rating;
    /**
    var importance = text.match(/class=".*import-(.*?)"/i);
    if(importance) {
        ret.importance = importance[1];
    } else {
        ret.importance = 'none';
    }
    */
    var importance = text.match(/\|\s*importance=\s*(.*?)\|/i);
    if(importance) {
        ret.importance = importance[1].toLowerCase();
    } else {
        ret.importance = 'none';
    }
    return ret;
}

// End calculation functions

function prepare_window_node(err, kwargs, callback) {
    var data                = kwargs.data,
        article_info        = kwargs.article_info,
        article             = kwargs.article,
        article_title       = article_info.article_title,
        article_id          = article_info.article_id,
        revision_id         = article_info.rev_id,
        text                = article.parse.text['*'];
    
    if (OUTPUT_HTML) { //TODO: create folder, escape article_title
        var fs       = require('fs');
        var out_file = fs.createWriteStream('article_html/'+article_title+'.html', {'flags': 'w', 'encoding':'utf8'});
        if (typeof out_file.setEncoding === 'function') {
            out_file.setEncoding('utf8');
        }
        out_file.write(text, 'utf8');
        out_file.destroySoon();
    }

    var window = wm.get_window(article_title);
    window.document.innerHTML = '<html><body>'+text+'</body></html>';
    
    var real_values = {
        'wgTitle': article_title,
        'wgArticleId': article_id,
        'wgCurRevisionId': revision_id,
        'wgCategories': article.parse.categories
    };

    var mw = {}; //building a mock object to look like mw (loaded on wikipedia by javascript)
    mw.config = {};
    mw.config.get = function(key) {
        return real_values[key] || null;
    };
    window.mw = mw; //attach mock object to fake window
    callback(null, window);
}

// This is a lower-level function, you probably want to use get_category()
function get_category_members(cat_name, limit, get_cm_callback, continue_str, results_so_far) {
    var url = 'http://en.wikipedia.org/w/api.php?action=query&generator=categorymembers&gcmtitle=' 
               + encodeURIComponent(cat_name)
               + '&prop=info&gcmlimit=' 
               + encodeURIComponent(limit) + '&format=json';
    if(continue_str) {
        url += '&gcmcontinue='+continue_str;
    }
    
    results_so_far = results_so_far || [];
    function cat_results_callback(err, data) {
        var pages, cont_str;
        try {
            cont_str = data['query-continue'].categorymembers.gcmcontinue;
        } catch (e) {
            cont_str = null;
        }
        // get page infos from data
        try {
            pages = data.query.pages;
        } catch (e) {
            pages = {};
            logger.error('Error finding pages in query results.');
        }

        logger.info(keys(pages).length + ' pages got.');
        
        for(var key in pages){
            var page = pages[key];
            results_so_far.push({'article_title': page.title.replace(/\s/g,'_'),
                                 'article_id'   : page.pageid,
                                 'rev_id'       : page.lastrevid,
                                 'ns'           : page.ns
                                });
        }
        //if not has continue || limit reached, call the real callback (aka evaluate articles)
        if (!cont_str || results_so_far.length >= limit) {
            get_cm_callback(null, results_so_far);
        } else {
            get_category_members(cat_name, limit, get_cm_callback, cont_str, results_so_far);
        }
    }
    do_query(url, cat_results_callback);
}

function get_cm_factory(name, limit) {
    return (function(queue_callback, retry) {
                get_category_members(name, limit, queue_callback);
            });
}

function get_cat_factory(name, limit, recursive, subcats, articles) {
    return (function(queue_callback, retry) {
            get_category(name, limit, recursive, queue_callback, subcats, articles);
        });
}

// TODO: prioritize breadth by enabling priority queue
function get_category(name, limit, recursive, get_cat_done_cb, subcats, articles) {
    limit = limit || ALL_CATS;
    recursive = recursive || false;
    
    subcats = subcats || {};
    articles = articles || {};
    function cat_callback_wrapper(real_cat_cb, subcats, articles) {
        return (function get_cat_callback(err, cat_mems) {
            if(err) {
                real_cat_cb(err, null);
            }
            for (var i=0; i<cat_mems.length; i += 1) {
                var mem = cat_mems[i];
                if (mem.ns == CATEGORY_NS) {
                    if (!(mem.article_id in subcats)) {
                        subcats[mem.article_id] = mem;
                        if (recursive) {
                            catq.enqueue(get_cm_factory(mem.article_title, limit),
                                         cat_callback_wrapper(real_cat_cb, subcats, articles));
                        }
                    }
                } else if (mem.ns == ARTICLE_NS){
                    if (!(mem.article_id in articles)) {
                        articles[mem.article_id] = mem;
                    }
                } else if (mem.ns == TALK_NS){
                    if(!(mem.article_id in articles)) {
                        articles[mem.article_id] = {'article_title': mem.article_title.replace('Talk:', '') };
                    }
                }
            }
            var article_count = keys(articles).length;
            var is_complete = (article_count >= limit) || catq.get_unfinished_count() <= 0;
            if( is_complete && !catq.is_closed ) {
                catq.stop();
                catq.close();
                real_cat_cb(null, values(articles).slice(0, limit));
            }
        });
    }
    catq.enqueue(get_cm_factory(name, limit),
                 cat_callback_wrapper(get_cat_done_cb, subcats, articles));
}

function evaluate_articles(infos, per_ev_cb) {
    var get_eval_wrapper = function(article_title, article_id, rev_id) {
        return function eval_article_wrapper(queue_callback, retry) { //TODO: use this retry?
            evaluate_article_node(article_title, article_id, rev_id, queue_callback);
        };
    };
    var get_eval_callback = function(article_title, per_ev_cb) {
        return function eval_callback(err, evaluator) {
            if (err) {
        err.title = article_title;
        per_ev_cb(err, null);
            } else {
                per_ev_cb(null, evaluator);
            }
        };
    };
    for (var i=0; i < infos.length; ++i) {
        var article_title = infos[i].article_title,
        article_id    = infos[i].article_id,
        rev_id        = infos[i].rev_id;
        

        jsdomq.enqueue(get_eval_wrapper(article_title, article_id, rev_id),
                       get_eval_callback(article_title, per_ev_cb));
    }
}

var ProgressManager = function ProgressManager(bar_names) {
    var self = {};
    //var multimeter = require('multimeter');
    
    var multi = self.multi = null; //multimeter(process); // TODO: make a working 'multimeter'
    //multi.charm.on('^C', process.exit);
    
    var bars = self.bars = {};
    
    var offset = 3;
    for (var i=0; i<bar_names.length; ++i) {
        offset = (offset < bar_names[i].length) ? bar_names[i].length : offset;
    }
    offset += 2; // room for colon + whitespace
    
    var config = {
        width : 50 - offset,
        solid : {
            text : '|',
            foreground : 'white',
            background : 'blue'
        },
        empty : { text : ' ' }
    };
    
    //multi.write('\nQualityVis progress and metrics:\n\n');
    for (var i=0; i<bar_names.length; ++i) {
        var name = bar_names[i];
        //multi.write(name+': \n');
        var bar = bars[name] = {};//multi.rel(offset, i, config);
        bar.last_n = 0;
        bar.last_d = false;
    }
    
    self.inc = function increment_progress(name) {
        return;
        var bar = self.bars[name];
        if (!bar) {
            logger.warning('Attempted to update unregistered progress bar: '+name);
            return;
        }
        var n = bar.last_n;
        var d = bar.last_d;
        if (d === false) {
            n = Math.min(n, 100);
            bar.percent(n);
        } else {
            bar.ratio(n, d || n); // if d is zero, avoid 0 division
        }
    };
    
    self.update = function update_progress(name, n, d) {
        return;
        var bar = self.bars[name];
        if (!bar) {
            logger.warning('Attempted to update unregistered progress meter: '+name);
            return;
        }
        
        var is_percent = !d && n <= 100 && n >= 0;
        if (is_percent) {
            bar.percent(n);
        } else {
            bar.ratio(n, d || n); // if d is zero, avoid 0 division
        }
    };
    
    self.destroy = function destroy_pm() {
        //self.multi.destroy();
    };
    return self;
};

function zero_fill(number, width) {
    width -= number.toString().length;
    if ( width > 0 ) {
	return new Array( width + (/\./.test( number ) ? 2 : 1) ).join( '0' ) + number;
    }
    return number + ""; // always return a string
}

// cat_name can be any string, but function has special handling for cat_name
// expected_count is some number, presumably
// start_time is a Date object
// extension is the file extension including the '.' (e.g., '.json')
function generate_filename(cat_name, expected_count, start_time, extension) {
    var path_lib = require('path');
    cat_name = cat_name.replace('Category:', '');
    var prefix = 'qv_' + cat_name + '_' + zero_fill(expected_count, 4) 
	+ '_' + start_time.getFullYear()
	+ ''  + zero_fill((start_time.getMonth()+1),2) 
	+ ''  + zero_fill(start_time.getDate(), 2);
    var filename = prefix + extension;
    if (path_lib.existsSync(filename)) {
	var suffix;
	for (var i=2; i<100; ++i) {
	    suffix = zero_fill(i,2);
	    if (!path_lib.existsSync(prefix+suffix+extension)) {
		filename = prefix + '_' + suffix + extension;
		break;
	    }
	}
    }
    return filename;
}

cli.main(function(args, options) {
    // update global constants
    EV_CONCURRENCY    = options.evaluator_workers;
    QUERY_CONCURRENCY = options.query_workers;
    CAT_CONCURRENCY   = options.cat_workers;
    GLOBAL_TIMEOUT    = options.global_timeout;
    
    mq     = queue(QUERY_CONCURRENCY, 'Query queue');
    jsdomq = queue(EV_CONCURRENCY, 'Evaluator queue');
    catq   = queue(CAT_CONCURRENCY, 'Category queue');

    var recursive     = options.recursive || false;
    var article_count = options.article_count;
    var category_name = options.category_name;
    var log_file      = options.log_file;
    var debug_mode    = options.debug;
    var start_time    = new Date();
    
    if (use_devnull) {
        if (!debug_mode) {
            logger.remove(stream_transport);
        }
	logger.use(stream_transport, {
                stream: require('fs').createWriteStream(log_file)
        });
        
        //try {
        pm = ProgressManager(['QVs']);
        pm.update('QVs', 0, article_count);
        /*} catch (e) {
            logger.warn('No multimeter module found, stdout is gonna be boring.');
            pm = {};
            pm.update = pm.inc = function() { return; } // mock multimeter
        }*/
    }
    logger.info('Started run at '+start_time);
    logger.info('Getting up to '+article_count+' articles from '+category_name+'.');

    wm = WindowManager(EV_CONCURRENCY + 2, null, function() {
        get_category(category_name, article_count, recursive, function(err, infos) {
            if(err) {
                console.error('Error retrieving entries for '+category_name);
                return;
            }
        
            var expected_count = infos.length;
            var complete_count = 0;
            var failed_titles = [];
            var successful_evs = [];

	    var csv_name = generate_filename(category_name, expected_count, start_time, '.csv');
	    var json_name = generate_filename(category_name, expected_count, start_time, '.json');
	    var json_output = get_json_output(json_name);
	    logger.info('Outputting results to '+csv_name);

            var per_ev_cb = function per_ev_cb(err, evaluator) {
                var dom, title;
                pm.inc('QVs');
                complete_count += 1;
                var count_message = ' (' + complete_count + '/' + expected_count + ')';
                if (err || !evaluator) {
                    dom   = err.dom;
                    title = (err && err.title) || 'Unknown article';
                    logger.warning('Failed to process article: ' + title + '. Dropping evaluator.' + count_message);
                    failed_titles.push(title);
                } else {
                    dom   = evaluator.dom;
                    title = evaluator.article_title;
                    logger.info('Successfully processed: '+title+count_message);
                    successful_evs.push(evaluator);
                    json_output(null, evaluator);
                    if (successful_evs.length > 0 && successful_evs.length % 10 === 0) {
			output_csv(successful_evs, csv_name);
                    }
                }
                wm.release_window(dom, title);

                
                if (complete_count >= expected_count) { // TODO overall timeout? timeout between evaluators completing?
                    var end_time = new Date();
                    var total_seconds = (end_time.valueOf() - start_time.valueOf()) / 1000;
                    logger.info('Batch evaluation complete at ' + end_time);
                    logger.info('Total time: ' + total_seconds + ' seconds.');
                    logger.info(failed_titles.length + '/' +complete_count + ' evaluations failed:');
                    logger.info(failed_titles);
                    output_csv(successful_evs, csv_name);
                }
            };

            evaluate_articles(infos, per_ev_cb);
        });
    });
});

function json_to_csv(json_filepath) {
    var data = require(json_filepath);
}

function escape_field(val) {
    var out_arr = [];
    if(typeof val === 'string') {
        for (var i = 0; i < val.length; i++) {
            if (val[i] === '"') {
                out_arr.push('"');
            }
            out_arr.push(val[i]);
        }
        return '"' + out_arr.join('') + '"';
    } else {
        return val;
    }
}

function is_outputtable(val) {
    var val_type = typeof val;
    return !(val_type === 'function' || val_type === 'object');
}

var begin_attrs = ['article_title', 'article_id', 'revision_id'];
var end_attrs = ['eval_date', 'assessment']
function output_csv(evaluators, path) {
    path = path || 'output_' + (new Date()).valueOf() + '.csv';
    var evs = [];
    //convert to dicts where necessary
    for (var i=0; i<evaluators.length; ++i) {
        if (!evaluators[i]) {
            continue;
        }
        if (typeof evaluators[i].to_dict === 'function')  {
            evs.push(evaluators[i].to_dict());
        } else {
            evs.push(evaluators[i]);
        }
    }
    //construct superset of stats for column headings
    var tmp_names = {};
    for (var i=0; i<evs.length; ++i) {
        var ev = evs[i];
        for (var stat in ev) {
            tmp_names[stat] = true;
        }
    }
    for (var stat in tmp_names) {
        var do_output = false;
        for (var j=0; j<evs.length; ++j) {
            var ev = evs[j];
            if (is_outputtable(ev[stat])) {
                do_output = true;
            }
        }
        if (!do_output) {
            delete tmp_names[stat];
        }
    }
    for (var i=0; i<begin_attrs.length; ++i) {
	delete tmp_names[begin_attrs[i]];
    }
    for (var i=0; i<end_attrs.length; ++i) {
	delete tmp_names[end_attrs[i]];
    }
    var col_names = [];
    col_names.push.apply(col_names, begin_attrs);
    col_names.push.apply(col_names, keys(tmp_names).sort());
    col_names.push.apply(col_names, end_attrs);
    
    var fs       = require('fs');
    var out_file = fs.createWriteStream(path, {'flags': 'w', 'encoding':'utf8'});
    if (typeof out_file.setEncoding === 'function') {
        out_file.setEncoding('utf8');
    }
    
    out_file.write(col_names.join(','));
    out_file.write('\n');
    for (var i=0; i<evs.length; ++i) {
        var ev = evs[i];
        for (var j=0; j<col_names.length; ++j) {
            var col_name = col_names[j];
            var cur_stat = ev[col_name];
            var to_write = (cur_stat !== null && cur_stat !== undefined) ? escape_field(cur_stat) : '';
            if (is_outputtable(cur_stat)) {
                out_file.write(to_write);
            } else {
                out_file.write('(object)');
            }
            out_file.write(',');
        }
        out_file.write('\n');
    }
    out_file.destroySoon();
    logger.info('CSV written to '+path);
}

function has_method(obj, meth_name) {
    if (typeof obj[meth_name] === 'function') {
	return true;
    } else {
	return false;
    }
}

function get_json_output(path) {
    var fs       = require('fs');
    var path     = path; //|| 'output_' + (new Date()).valueOf()+'.json';
    var all_ev_outputs = {};
    return function save_ev(err, ev) {
        var to_save = ev.to_dict();
        
        var out_file = fs.createWriteStream(path, {'flags': 'w', 'encoding':'utf8'});
        if ( has_method(out_file, 'setEncoding') ) { 
            out_file.setEncoding('utf8');
        }
        all_ev_outputs[ev.article_title] = to_save;
        out_file.write(JSON.stringify(all_ev_outputs));
        out_file.destroySoon();
    };
}

function get_info_callback(real_callback) {
    return function info_callback(err, data) {
        var get_info_failed = (err || !(data && data.fetch_data.query));
        if (get_info_failed) {
            logger.error(data);
            logger.info('error getting article info. maybe timed out?');
            return;
        }
        var page_ids = keys(data.fetch_data.query.pages),
            pages    = data.fetch_data.query.pages;
        
        if (page_ids.length === 0) {
            logger.info('No article with title ' + article_title + ' found.');
            return;
        }
        var article_id    = page_ids[0],
            article_title = pages[article_id].title.replace(/ /g, '_'),
            rev_id        = pages[article_id].revisions[0].revid,
            prev_rev_id   = pages[article_id].revisions[0].parentid;
        real_callback(null,{results: {article_title: article_title,
                             article_id: article_id,
                             rev_id: rev_id}
                         });
    };
};


function evaluate_article_node(article_title, article_id, rev_id, eval_callback) {
    Step(
        function start() {
            logger.info("Start QV on "+article_title);
            
            var info_callback = this.parallel();
            var content_callback = this.parallel();
            if (!article_id || !rev_id) {
                // first order of business, wrap in processing function
                info_callback = get_info_callback(info_callback);
                var info_input = input('get_article_info',
                                       web_source('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=' + article_title+'&rvprop=ids&redirects=true&format=json')
                                       );
                mq.enqueue(info_input, info_callback);
            } else {
                info_callback(null,{results: { article_title: article_title,
                                            article_id   : article_id,
                                            rev_id       : rev_id
                                            }
                                    }
                              );
            }
            
            var content_input = input('get_article_content',
                                      web_source('http://en.wikipedia.org/w/api.php?action=parse&page='+article_title+'&format=json&redirects=true')
                                      );
            mq.enqueue(content_input, content_callback);
        },
        function prepare_window(err, info_input, content_input) {
            if (err) {
                logger.error('Error retrieving info for article "'+article_title+'"');
                throw err;
            }
            prepare_window_node(err, {'article_info': info_input.results,
                                      'article': content_input.results},
                                this);
        },
        function make_evaluator_wrapper(err, window) {
            if (err) {
                logger.error('Could not construct window: '+err);
                throw err;
            }
            var ev = make_evaluator(window, rewards, this, mq);
        },
        function all_done(err, evaluator) {
            if (err) {
                logger.error('Could not evaluate article: '+err);
                if(eval_callback) {
                    eval_callback(err, null);
                } else {
                    throw err;
                }
            } else {
                logger.info('Successfully finished '+evaluator.article_title);
                if (eval_callback) {
                    eval_callback(null, evaluator);
                }
            }
        }
    );
}
