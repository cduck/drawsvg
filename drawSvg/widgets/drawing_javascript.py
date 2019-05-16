javascript = '''
require.undef('drawingview');

define('drawingview', ["@jupyter-widgets/base"], function(widgets) {
    var DrawingView = widgets.DOMWidgetView.extend({
        render: function() {
            this.container = document.createElement('a');
            this.image_changed();
            this.container.appendChild(this.svg_view);
            this.el.appendChild(this.container);
            this.model.on('change:_image', this.image_changed, this);
        },
        image_changed: function() {
            this.container.innerHTML = this.model.get('_image');
            this.svg_view = this.container.getElementsByTagName('svg')[0];
            this.cursor_point = this.svg_view.createSVGPoint();
            this.register_events();
        },
        send_mouse_event: function(name, e) {
            if (this.model.get('disable')) {
                return;
            }
            if (this.model.get('throttle')) {
                this.model.set('_mousemove_blocked', true);
                this.model.save_changes();
            }

            this.cursor_point.x = e.clientX;
            this.cursor_point.y = e.clientY;
            var svg_pt = this.cursor_point.matrixTransform(
                            this.svg_view.getScreenCTM().inverse());

            this.send({
                name: name,
                x: svg_pt.x,
                y: -svg_pt.y,
                type: e.type,
                button: e.button,
                buttons: e.buttons,
                shiftKey: e.shiftKey,
                altKey: e.altKey,
                ctrlKey: e.ctrlKey,
                metaKey: e.metaKey,
                clientX: e.clientX,
                clientY: e.clientY,
                movementX: e.movementX,
                movementY: e.movementY,
                timeStamp: e.timeStamp,
                targetId: e.target ? e.target.id : null,
                currentTargetId: e.currentTarget ? e.currentTarget.id : null,
                relatedTargetId: e.relatedTarget ? e.relatedTarget.id : null,
            });
        },
        register_events: function() {
            var widget = this;
            this.svg_view.addEventListener('mousedown', function(e) {
                e.preventDefault();
                widget.send_mouse_event('mousedown', e);
            });
            this.svg_view.addEventListener('mousemove', function(e) {
                e.preventDefault();
                if (!widget.model.get('_mousemove_blocked')) {
                    widget.send_mouse_event('mousemove', e);
                }
            });
            this.svg_view.addEventListener('mouseup', function(e) {
                e.preventDefault();
                widget.send_mouse_event('mouseup', e);
            });
        }
    });

    return {
        DrawingView: DrawingView
    };
});
'''
