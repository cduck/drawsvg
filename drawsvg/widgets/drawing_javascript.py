javascript = '''
require.undef('drawingview');

define('drawingview', ['@jupyter-widgets/base'], function(widgets) {
    class DrawingModel extends widgets.DOMWidgetModel {
        defaults() {
            return {
                ...super.defaults(),
                _model_name: DrawingModel.model_name,
                _model_module: DrawingModel.model_module,
                _model_module_version: DrawingModel.model_module_version,
                _view_name: DrawingModel.view_name,
                _view_module: DrawingModel.view_module,
                _view_module_version: DrawingModel.view_module_version,
            };
        }
        static serializers = {
            ...widgets.DOMWidgetModel.serializers,
        };
        static model_name = 'DrawingModel';
        static model_module = 'drawingview';
        static model_module_version = '0.1.0';
        static view_name = 'DrawingView';
        static view_module = 'drawingview';
        static view_module_version = '0.1.0';
    }

    class DrawingView extends widgets.DOMWidgetView {
        render() {
            this.container = document.createElement('a');
            this.image_changed();
            this.container.appendChild(this.svg_view);
            this.el.appendChild(this.container);
            this.model.on('change:_image', this.image_changed, this);
            this.model.on('change:_mousemove_blocked', this.block_changed,
                          this);
            this.model.on('change:frame_delay', this.delay_changed,
                          this);
            this.model.on('change:_frame_blocked', this.delay_changed,
                          this);
            this.model.on('change:disable', this.delay_changed,
                          this);
            this.delay_changed();
        }
        image_changed() {
            this.container.innerHTML = this.model.get('_image');
            this.svg_view = this.container.getElementsByTagName('svg')[0];
            this.cursor_point = this.svg_view.createSVGPoint();
            this.register_events();
        }
        last_move = null;
        last_mousemove_blocked = null;
        last_timer = null;
        block_changed() {
            var widget = this;
            window.setTimeout(function() {
                if (widget.model.get('_mousemove_blocked')
                        != widget.last_mousemove_blocked && widget.last_move) {
                    widget.send_mouse_event('mousemove', widget.last_move);
                }
            }, 0);
        }
        send_mouse_event(name, e) {
            this.last_move = null;
            if (this.model.get('disable')) {
                return;
            }

            this.cursor_point.x = e.clientX;
            this.cursor_point.y = e.clientY;
            var svg_pt = this.cursor_point.matrixTransform(
                            this.svg_view.getScreenCTM().inverse());

            var target_parents = [];
            var target = e.target;
            while(target && target != this.svg_view)
            {
                if (target.id) {
                    target_parents.push(target.id);
                }
                target = target.parentNode;
            }

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
                targetParentIds: target_parents,
                currentTargetId: e.currentTarget ? e.currentTarget.id : null,
                relatedTargetId: e.relatedTarget ? e.relatedTarget.id : null,
            });
        }
        delay_changed() {
            var widget = this;
            window.clearTimeout(widget.last_timer);
            if (widget.model.get('disable')) {
                return;
            }
            var delay = widget.model.get('frame_delay');
            if (delay > 0) {
                widget.last_timer = window.setTimeout(function() {
                    widget.send_timed_event('timed');
                }, delay);
            }
        }
        send_timed_event(name) {
            if (this.model.get('disable')) {
                return;
            }

            this.send({
                name: name,
            });
        }
        register_events() {
            var widget = this;
            this.svg_view.addEventListener('mousedown', function(e) {
                e.preventDefault();
                widget.send_mouse_event('mousedown', e);
            });
            this.svg_view.addEventListener('mousemove', function(e) {
                e.preventDefault();
                if (widget.model.get('_mousemove_blocked')
                        == widget.last_mousemove_blocked) {
                    widget.last_move = e;
                } else {
                    widget.send_mouse_event('mousemove', e);
                }
            });
            this.svg_view.addEventListener('mouseup', function(e) {
                e.preventDefault();
                widget.send_mouse_event('mouseup', e);
            });
        }
    }

    return {
        DrawingModel: DrawingModel,
        DrawingView: DrawingView
    };
});
'''
