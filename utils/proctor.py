import re

MAX_ALLOWED_SWITCHES = 2  # a 3rd tab switch stops and flags the attempt


def _safe_key(quiz_key):
    return re.sub(r"[^a-zA-Z0-9_]", "_", str(quiz_key))


def read_tab_switch_count(streamlit_js_eval, quiz_key):
    """
    Attaches (once per browser session) a visibilitychange listener on the
    parent document that increments a sessionStorage counter every time the
    tab is hidden, then returns the current counter value. Safe to call on
    every autorefresh tick; the listener is only ever attached once thanks
    to the __ts_<key> guard flag stashed on window.parent.
    """
    skey = _safe_key(quiz_key)
    storage_key = f"tabswitch_{skey}"
    guard_flag = f"__ts_listener_{skey}"

    js = f"""
    (function() {{
        try {{
            var w = window.parent;
            if (!w.{guard_flag}) {{
                w.{guard_flag} = true;
                if (w.sessionStorage.getItem('{storage_key}') === null) {{
                    w.sessionStorage.setItem('{storage_key}', '0');
                }}
                w.document.addEventListener('visibilitychange', function() {{
                    if (w.document.hidden) {{
                        var c = parseInt(w.sessionStorage.getItem('{storage_key}') || '0') + 1;
                        w.sessionStorage.setItem('{storage_key}', c.toString());
                    }}
                }});
            }}
            return w.sessionStorage.getItem('{storage_key}') || '0';
        }} catch (e) {{
            return '0';
        }}
    }})()
    """
    result = streamlit_js_eval(js_expressions=js, key=f"proctor_{skey}_poll")
    try:
        return int(result)
    except (TypeError, ValueError):
        return 0


def reset_tab_switch_count(streamlit_js_eval, quiz_key):
    skey = _safe_key(quiz_key)
    storage_key = f"tabswitch_{skey}"
    js = f"""
    (function() {{
        try {{ window.parent.sessionStorage.setItem('{storage_key}', '0'); return '0'; }}
        catch (e) {{ return '0'; }}
    }})()
    """
    streamlit_js_eval(js_expressions=js, key=f"proctor_{skey}_reset_{quiz_key}")
