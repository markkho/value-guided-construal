/*
Requires
	- raphael
	- lodash
	- jquery
*/

import {product} from "./utils.js"

var default_config = {
	TILE_SIZE : 150,
	AGENT_COLORS : ['blue', 'green', 'red'],
	PRIMARY_AGENT_COLOR : 'orange',
	AGENT_WIDTH : .3,
	WALL_WIDTH : .12,
	WALL_STROKE_SIZE : 10,
	CONTRACT_SIZE : .9,
	SUBACTION_PROPORTION : .2,
	SUBACTION_DISTANCE : .2,
	SUBACTION_COLLISION_PROPORTION : .7,
	SUBACTION_COLLISION_DISTANCE : .7,
	REWARD_DISPLAY_TIME : 1000,
	DISPLAY_BORDER : 20,

	sprite_color_to_offset : {
		'white': {row : 0, col : 0},
		'brown': {row : 0, col : 3},
		'yellow': {row : 0, col : 6},
		'red': {row : 0, col : 9},
		'lightbrown': {row : 4, col : 0},
		'grey': {row : 4, col : 3},
		'brownspot': {row : 4, col : 6},
		'greyspot': {row : 4, col : 9}
	},

	//timing parameters
	OBJECT_ANIMATION_TIME : 1000,
	SPRITE_STEPPING_FRAME_TIME : 100,
	SPRITE_MOVING_FRAME_TIME : 50,
	SPRITE_CIRCLING_FRAME_TIME : 250
};

export var GridWorldPainter = function (width, height, container, config) {
	config = typeof(config) === 'undefined' ? {} : config;
	_.defaults(config, default_config);
	for (var key in config) {
		this[key] = config[key];
	}
	var painter = this;

	painter.container = container;
	painter.width = width;
	painter.height = height;
	painter.width_px = width*painter.TILE_SIZE+painter.DISPLAY_BORDER*2;
	painter.height_px = height*painter.TILE_SIZE+painter.DISPLAY_BORDER*2;

	painter.y_to_h = function (y) {
		return height - (y + 1)
	}

	painter.h_to_y = function (h) {
		return height - h - 1
	}

	painter.objects = {};
	painter.orientation_to_rotation = {'^':0, '>':90, 'v':180, '<':270};
}

GridWorldPainter.prototype.initialize_paper = function () {
	var painter = this;
	painter.paper = Raphael(
	    painter.container,
        painter.width*painter.TILE_SIZE+2*painter.DISPLAY_BORDER,
		painter.height*painter.TILE_SIZE+2*painter.DISPLAY_BORDER);
}


/*=============================================================================


					Drawing Tiles, Text, and Walls


=============================================================================*/
GridWorldPainter.prototype.draw_tiles = function (tile_params) {
	//tile_params is a mapping from states to raphael parameters
	var painter = this;

	//clear tiles before redrawing
	if (typeof(painter.tiles) !== 'undefined') {
		_(painter.tiles).forEach(function (tile) {
			tile.remove();
		});
	}
	painter.tiles = [];
	painter.xy_to_tiles = {};

	var states = product([_.range(painter.width), _.range(painter.height)]);
	if (typeof(tile_params) === 'undefined') {
		tile_params = _.fromPairs(_.map(states, function (s) {return [s, {}]}));
	}
	else {
		_(states).forEach(function (state) {
			if (!_.includes(_.keys(tile_params), String(state))) {
				tile_params[state] = {}
			}
		});
	}

	_(tile_params).forEach($.proxy(function (params, state) {
			var xy = _.map(state.split(','), parseFloat);
			var x = xy[0];
			var y = xy[1];
			var default_tile_params = {
				fill : 'white',
				type : 'rect',
				x : x*this.TILE_SIZE+this.DISPLAY_BORDER,
				y : this.y_to_h(y)*this.TILE_SIZE+this.DISPLAY_BORDER,
				width : this.TILE_SIZE,
				height : this.TILE_SIZE,
				stroke : 'black'
			};
			// params = Object.assign({}, params);
			// params = _.cloneDeep(params);
	        params = JSON.parse(JSON.stringify(params));
			_.defaults(params, default_tile_params);
			var tile = this.paper.add([params])[0];
			tile.grid_xy = xy;
			this.tiles.push(tile);
			this.xy_to_tiles[xy] = tile;
		}, this))
}

GridWorldPainter.prototype.add_text = function({
                                                   x,
                                                   y,
                                                   text,
                                                   text_params = {}}) {

	var painter = this;
	var params = {
		type : 'text',
		x : (x + .5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
		y : (painter.y_to_h(y)+.5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
		text : text,
		"font-size" : painter.TILE_SIZE/text.length
	};
	_.assign(params, text_params);
	var mytext = painter.paper.add([params])[0];
	return mytext
};

GridWorldPainter.prototype.float_text = function({
                                     x, y, text,
                                     pre_params = {},
                                     post_params = {},
                                     dx = 0,
                                     dy = .5,
                                     anim_type = 'easeOutIn',
                                     anim_time = this.REWARD_DISPLAY_TIME
}) {
    // pre_params = typeof(pre_params) === 'undefined' ? {} : pre_params;
    // post_params = typeof(post_params) === 'undefined' ? {} : post_params;
    // anim_type = typeof(anim_type) === 'undefined' ? 'easeOutIn' : anim_type;
    // dx = typeof(dx) === 'undefined' ? 0 : dx;
    // dy = typeof(dy) === 'undefined' ? .5 : dy;
    // anim_time = typeof(anim_time) === 'undefined' ? painter.REWARD_DISPLAY_TIME : anim_time;

	var painter = this;
	var start_params = {
		type : 'text',
		x : (x + .5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
		y : (painter.y_to_h(y)+.5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
		text : text,
		"font-size" : painter.TILE_SIZE/text.length
	};
	_.assign(start_params, pre_params);
	var mytext = painter.paper.add([start_params])[0];

    var animate_params = {
        y : start_params.y+(painter.TILE_SIZE*(-dy)),
        x : start_params.x+(painter.TILE_SIZE*(dx)),
        opacity : 0
    };
    _.assign(animate_params, post_params);
	var animate = Raphael.animation(animate_params,
        anim_time,
        anim_type,
        function () {
			mytext.remove();
		});
	mytext.animate(animate);
	return anim_time
};

GridWorldPainter.prototype.float_image = function(x, y, src, width, height,
                                                  display_time, params) {
	display_time = typeof(display_time) === 'undefined' ? this.REWARD_DISPLAY_TIME : display_time;
	var start_params = {
		type : 'image',
		x : (x + .5)*this.TILE_SIZE+this.DISPLAY_BORDER-width/2,
		y : (this.y_to_h(y) + .5)*this.TILE_SIZE+this.DISPLAY_BORDER-height/2,
		src : src,
		width : width,
		height : height
	}
	_.assign(start_params, params);
	var my_img = this.paper.add([start_params])[0];
	var animate = Raphael.animation({
		y : start_params.y-(this.TILE_SIZE*.5),
		opacity : 0
	}, display_time, 'easeOutIn', (function (my_img) {
		return function () {
					my_img.remove();
				}
	})(my_img));
	my_img.animate(animate);
	return display_time
}

GridWorldPainter.prototype.draw_wall = function(x, y, side, id, params) {
	params = typeof(params) === 'undefined' ? {} : params;
	var painter = this;
	var wall_width = this.WALL_WIDTH;
	y = painter.y_to_h(y);

	if (typeof(side) === 'undefined') {
		var default_wall_params = {
			fill : 'black',
			type : 'rect',
			x : (x-wall_width/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
			y : (y-wall_width/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
			width : painter.TILE_SIZE*(1+wall_width),
			height : painter.TILE_SIZE*(1+wall_width),
			stroke : 'black'
		};
		_.defaults(params, default_wall_params);
		var wall = painter.paper.add([params])[0];
	} else {
	    var start_x, start_y, end_x, end_y;
		if (side === '>') {
			start_x = x + 1 - wall_width;
			start_y = y;
			height = 1;
			width = wall_width;
		}
		else if (side === 'v') {
		    start_x = x;
		    start_y = y+1-wall_width;
		    height = wall_width;
		    width = 1;
		}
		else if (side === '<') {
		    start_x = x;
		    start_y = y;
		    height = 1;
		    width = wall_width;
		}
		else if (side === '^') {
		    start_x = x;
		    start_y = y;
		    height = wall_width;
		    width = 1;
		}

		var default_wall_params = {
			fill : '#000000',
			type : 'rect',
			x : start_x*this.TILE_SIZE+painter.DISPLAY_BORDER,
			y : start_y*this.TILE_SIZE+painter.DISPLAY_BORDER,
			width : width*this.TILE_SIZE,
			height : height*this.TILE_SIZE,
			stroke : 'black',
            // "stroke-weight" : 2
		};
		_.defaults(params, default_wall_params);
		var wall = painter.paper.add([params])[0];
	}
    painter.objects[id] = {
        object_type : "wall",
        object_id : id,
        object_params : params,
        drawn_object : wall
    };
}

GridWorldPainter.prototype.draw_walls = function(walls) {
	for (var w = 0; w < walls.length; w++) {
		var wall = walls[w];
		this.draw_wall(wall.x, wall.y, wall.side, wall.params)
	}
}

/*=============================================================================


				  Initializing, Drawing, and Clearing Objects


=============================================================================*/
GridWorldPainter.prototype.add_object = function
    (object_type, object_id, object_params) {
	//support for circle, rect, and sprite - default values are set here
	var painter = this;
	if (object_type == 'circle') {
		_.defaults(object_params, {
			agent_size : .3
		})
	}
	else if (object_type == 'rect') {
		_.defaults(object_params, {
			object_length : .8,
			object_width : .5
		});
	}
	else if (object_type == 'sprite') {
		var spritecolor = typeof(object_params['spritecolor']) == 'undefined' ? 'white' : object_params['spritecolor'];
		var orientation_step_to_row_col = (function (offset) {
			return function (orientation, step) {
				var o_to_r = {'v' : 0, '^' : 3, '<' : 1, '>' : 2};
				var row = o_to_r[orientation];
				var col = step%3
				return [row+offset.row, col+offset.col]
			}
		})(this.sprite_color_to_offset[spritecolor]);

		_.defaults(object_params, {
			sheet_rows : 8,
			sheet_cols : 12,
			src : './img/dogSpriteSheet.png',
			orientation_step_to_row_col : orientation_step_to_row_col,
			x_adj : 0,
			y_adj: -5
		});
	}
	painter.objects[object_id] = {
		object_type : object_type,
		object_id : object_id,
		object_params : object_params
	}
}

GridWorldPainter.prototype.draw_object = function(x, y, orientation, object_id) {
	var painter = this;

	/*========================================================================
								Drawing a circle
	========================================================================*/
	if (painter.objects[object_id].object_type == 'circle') {
		if (typeof(painter.objects[object_id].drawn_object) == 'undefined') {
			//default circle params
			var object_params = painter.objects[object_id].object_params;
			var params = {
				type : 'circle',
				cx : (x + .5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
				cy : (painter.y_to_h(y)+.5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
				fill : 'blue',
				r : this.TILE_SIZE*object_params.agent_size,
				stroke : 'white',
				'stroke-width' : 1
			};
			_.assign(params, object_params)
			var drawn_object = painter.paper.add([params])[0];
			painter.objects[object_id].drawn_object = drawn_object;
		}
		else {
			painter.objects[object_id].drawn_object.attr({
				cx : (x + .5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
				cy : (painter.y_to_h(y)+.5)*painter.TILE_SIZE+painter.DISPLAY_BORDER
			});
		}
	}
	/*========================================================================
								Drawing a rectangle
	========================================================================*/
	if (painter.objects[object_id].object_type == 'rect') {
		var object_params = painter.objects[object_id].object_params;
		if (_.includes(['^','v'], orientation)) {
			var rect_width = object_params.object_width;
			var rect_length = object_params.object_length;
		}
		else if (_.includes(['<', '>'], orientation)) {
			var rect_width = object_params.object_length;
			var rect_length = object_params.object_width;
		}

		//whether a drawn object exists or not
		if (typeof(painter.objects[object_id].drawn_object) == 'undefined') {
			//default rectangle params
			var params = {
				type : 'rect',
				x : (x+.5-rect_width/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
				y : (painter.y_to_h(y)+.5-rect_length/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
				width : rect_width*painter.TILE_SIZE,
				height : rect_length*painter.TILE_SIZE,
				fill : 'blue',
				stroke : 'white',
				'stroke-width' : 1
			}
			_.assign(params, object_params)
			var drawn_object = painter.paper.add([params])[0];
			painter.objects[object_id].drawn_object = drawn_object;
		}
		else {
			painter.objects[object_id].drawn_object.attr({
				x : (x+.5-rect_width/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
				y : (painter.y_to_h(y)+.5-rect_length/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
				width : rect_width*painter.TILE_SIZE,
				height : rect_length*painter.TILE_SIZE
			});
		}
	}

	/*========================================================================
								Drawing a sprite
	========================================================================*/
	if (painter.objects[object_id].object_type == 'sprite') {
		var sprite_params = painter.objects[object_id].object_params;
		var s_rowcol = sprite_params.orientation_step_to_row_col(orientation, 1);
		var s_row = s_rowcol[0];
		var s_col = s_rowcol[1];

		var params = {
			x : (x-s_col)*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.x_adj,
			y : (painter.y_to_h(y)-s_row)*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.y_adj,

			'clip-rect':_.join([
					x*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.x_adj,
					painter.y_to_h(y)*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.y_adj+2,
					painter.TILE_SIZE,
					painter.TILE_SIZE
				], ',')
		}
		if (typeof(painter.objects[object_id].drawn_object) == 'undefined') {
			_.defaults(params, {
				width : painter.TILE_SIZE*sprite_params.sheet_cols,
				height : painter.TILE_SIZE*sprite_params.sheet_rows,
				src : sprite_params.src,
				type: 'image'
			});
			_.assign(params, sprite_params);
			var drawn_object = painter.paper.add([params])[0];
			painter.objects[object_id].drawn_object = drawn_object;
		}
		else {
			painter.objects[object_id].drawn_object.attr(params);
		}
		painter.objects[object_id].object_params.sprite_step = 1;
	}

	//update parameters of object
	painter.objects[object_id].object_params.grid_x = x;
	painter.objects[object_id].object_params.grid_y = y;
	painter.objects[object_id].object_params.orientation = orientation;
}

GridWorldPainter.prototype.hide_object = function(object_id) {
	this.objects[object_id].drawn_object.hide();
}

GridWorldPainter.prototype.show_object = function(object_id) {
	this.objects[object_id].drawn_object.show();
}

GridWorldPainter.prototype.clear_objects = function() {
	_.forEach(this.objects, function (object, object_id) {
		object.drawn_object.remove();
	})
	this.objects = {};
}

GridWorldPainter.prototype.clear_object = function(object_id) {
	this.objects[object_id].drawn_object.remove();
	this.objects[object_id] = undefined;
}

/*================================================================================================


										Animating Objects


================================================================================================*/

GridWorldPainter.prototype._update_sprite = function(object_id, params) {
	//params available: orientation, sprite_step, grid_x, grid_y
	var painter = this;
	var sprite_params = painter.objects[object_id].object_params;

	var orientation = typeof(params.orientation) == 'undefined' ? sprite_params.orientation : params.orientation;
	var sprite_step = typeof(params.sprite_step) == 'undefined' ? sprite_params.sprite_step : params.sprite_step;
	var grid_x = typeof(params.grid_x) == 'undefined' ? sprite_params.grid_x : params.grid_x;
	var grid_y = typeof(params.grid_y) == 'undefined' ? sprite_params.grid_y : params.grid_y;

	var s_rowcol = sprite_params.orientation_step_to_row_col(orientation, sprite_step);
	var s_row = s_rowcol[0];
	var s_col = s_rowcol[1];

	var drawn_sprite = painter.objects[object_id].drawn_object;
	drawn_sprite.attr({
			x : (grid_x-s_col)*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.x_adj,
			y : (painter.y_to_h(grid_y)-s_row)*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.y_adj,

			'clip-rect':_.join([
					grid_x*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.x_adj,
					painter.y_to_h(grid_y)*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.y_adj+2,
					painter.TILE_SIZE,
					painter.TILE_SIZE
				], ',')
		}
	);
	_.assign(sprite_params, params, {sheet_cols : s_col, sheet_rows : s_row});
};


GridWorldPainter.prototype.animate_object_movement = function
    ({action, new_x, new_y,
     object_id,
     anim_type = 'easeInOut',
     distance = 1,
	 OBJECT_ANIMATION_TIME = this.OBJECT_ANIMATION_TIME}) {
	var painter = this;

	new_x -= (new_x - painter.objects[object_id].object_params.grid_x)*(1-distance);
	new_y -= (new_y - painter.objects[object_id].object_params.grid_y)*(1-distance);

	/*========================================================================
								Animate a circle
	========================================================================*/
	if (painter.objects[object_id].object_type == 'circle') {
		var object_params = painter.objects[object_id].object_params;
		var drawn_object = painter.objects[object_id].drawn_object;

		if (action == 'x') {
			var expand_animate = Raphael.animation({r : painter.TILE_SIZE*object_params.agent_size},
													OBJECT_ANIMATION_TIME*.5, 'backOut');
			var expand = (function (drawn_object, expand_animate) {
				return function () {
					drawn_object.animate(expand_animate)
				}
			})(drawn_object, expand_animate)
			var contract = Raphael.animation({
												r : painter.TILE_SIZE*object_params.agent_size*painter.CONTRACT_SIZE,
												cx : (new_x + .5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
												cy : (painter.y_to_h(new_y)+.5)*painter.TILE_SIZE+painter.DISPLAY_BORDER
											},
											 OBJECT_ANIMATION_TIME*.5,
											 'backIn', expand);
			drawn_object.animate(contract);
		}
		else {
			var move = Raphael.animation({
					cx : (new_x + .5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
					cy : (painter.y_to_h(new_y)+.5)*painter.TILE_SIZE+painter.DISPLAY_BORDER
				},OBJECT_ANIMATION_TIME, anim_type);
			drawn_object.animate(move);
			object_params.grid_x = new_x;
			object_params.grid_y = new_y;
		}
	}

	/*========================================================================
							Animate a rectangle
	========================================================================*/
	if (painter.objects[object_id].object_type == 'rect') {
		var object_params = painter.objects[object_id].object_params;
		var drawn_object = painter.objects[object_id].drawn_object;

		if (_.includes(['^','v','<','>'], action)) {
			object_params.orientation = action;
		}
		if (_.includes(['^','v'], object_params.orientation)) {
			var rect_width = object_params.object_width;
			var rect_length = object_params.object_length;
		}
		else if (_.includes(['<', '>'], object_params.orientation)) {
			var rect_width = object_params.object_length;
			var rect_length = object_params.object_width;
		}

		if (action == 'x') {
			var expand_animate = Raphael.animation({
													width : rect_width*painter.TILE_SIZE,
													height : rect_length*painter.TILE_SIZE,
													x : drawn_object.attr('x'),
													y : drawn_object.attr('y')
													},
													OBJECT_ANIMATION_TIME*.5, 'backOut');
			var expand = (function (drawn_object, expand_animate) {
				return function () {
					drawn_object.animate(expand_animate)
				}
			})(drawn_object, expand_animate)
			var contract = Raphael.animation({
												width : rect_width*painter.TILE_SIZE*painter.CONTRACT_SIZE,
												height : rect_length*painter.TILE_SIZE*painter.CONTRACT_SIZE,
												x : (new_x+.5-(rect_width*painter.CONTRACT_SIZE)/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
												y : (painter.y_to_h(new_y)+.5-(rect_length*painter.CONTRACT_SIZE)/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER
											},
											 OBJECT_ANIMATION_TIME*.5,
											 'backIn', expand);
			drawn_object.animate(contract);
		}
		else {
			painter.draw_object(object_params.grid_x, object_params.grid_y, action, object_id);
			var move = Raphael.animation({
					x : (new_x+.5-rect_width/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
					y : (painter.y_to_h(new_y)+.5-rect_length/2)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
					width : rect_width*painter.TILE_SIZE,
					height : rect_length*painter.TILE_SIZE
				},OBJECT_ANIMATION_TIME, anim_type);
			drawn_object.animate(move);
			object_params.grid_x = new_x;
			object_params.grid_y = new_y;
		}
	}
	/*========================================================================
								Animate a sprite
	========================================================================*/
	if (painter.objects[object_id].object_type == 'sprite') {
		var SPRITE_STEPPING_FRAME_TIME = painter.SPRITE_STEPPING_FRAME_TIME;
		var SPRITE_CIRCLING_FRAME_TIME = painter.SPRITE_CIRCLING_FRAME_TIME;
		var SPRITE_MOVING_FRAME_TIME = painter.SPRITE_MOVING_FRAME_TIME;

		var sprite_params = painter.objects[object_id].object_params;

		var frames = OBJECT_ANIMATION_TIME/SPRITE_MOVING_FRAME_TIME;
		var dx = (new_x - sprite_params.grid_x)/frames;
		var dy = (new_y - sprite_params.grid_y)/frames;

		painter.objects[object_id].timers = {};
		var timers = painter.objects[object_id].timers;

		if (_.includes(['>','v','<','^'], action)) {
			painter._update_sprite(object_id, {orientation : action});

			var sprite_moving = (function (painter, object_id, sprite_params, dx, dy) {
				return function () {
					painter._update_sprite(object_id, {
						grid_x : sprite_params.grid_x+dx,
						grid_y : sprite_params.grid_y+dy
					})
				}
			})(painter, object_id, sprite_params, dx, dy)
			var moving = setInterval(sprite_moving, SPRITE_MOVING_FRAME_TIME);
			timers['moving'] = moving;



			var sprite_stepping = (function (painter, object_id, sprite_params) {
				return function () {
					if (sprite_params.sprite_step == 0) {var step = 2}
					else {var step = 0}
					painter._update_sprite(object_id, {sprite_step:step});
				}
			})(painter, object_id, sprite_params)
			var stepping = setInterval(sprite_stepping, SPRITE_STEPPING_FRAME_TIME);
			timers['stepping'] = stepping;


			var kill_animation = (function (painter, object_id, stepping, moving, new_x, new_y) {
				return function () {
					painter._update_sprite(object_id, {grid_x:new_x, grid_y:new_y})
					painter._update_sprite(object_id, {sprite_step:1});
					clearInterval(stepping);
					clearInterval(moving);
				}
			})(painter, object_id, stepping, moving, new_x, new_y);

			timers['kill_animation'] = setTimeout(kill_animation, OBJECT_ANIMATION_TIME);
		}
		else if (action == 'x') {
			var original_orientation = sprite_params.orientation;
			var sprite_circling = (function (painter, object_id, sprite_params) {
				var next_orientation = {'>':'v', 'v':'<', '<':'^', '^':'>'};
				return function () {
					painter._update_sprite(object_id, {orientation:next_orientation[sprite_params.orientation]})
				}
			})(painter, object_id, sprite_params)
			var circling = setInterval(sprite_circling, SPRITE_CIRCLING_FRAME_TIME);
			timers['circling'] = circling;

			var kill_animation = (function (painter, object_id, circling, original_orientation) {
				return function () {
					painter._update_sprite(object_id, {orientation : original_orientation});
					clearInterval(circling)
				}
			})(painter, object_id, circling, original_orientation);

			timers['kill_animation'] = setTimeout(kill_animation, OBJECT_ANIMATION_TIME)
		}


	}

	return painter.OBJECT_ANIMATION_TIME;
};

GridWorldPainter.prototype.kill_object_movement = function (object_id) {
	if ((this.objects[object_id].object_type === 'circle') ||
		(this.objects[object_id].object_type === 'rect')) {
		this.objects[object_id].drawn_object.stop()
	}
	else if (this.objects[object_id].object_type === 'sprite') {
		var timers = this.objects[object_id].timers;

		//kill animation
		if (_.has(timers, 'stepping')) {
			clearInterval(timers.stepping);
		}
		if (_.has(timers, 'moving')) {
			clearInterval(timers.moving);
		}
		if (_.has(timers, 'circling')) {
			clearInterval(timers.circling);
		}
		if (_.has(timers, 'kill_animation')) {
			clearTimeout(timers.kill_animation);
		}
	}
};

GridWorldPainter.prototype.bring_objects_into_contact = function
    (obj1_id, obj2_id, obj1_weight, overlap, config) {
    config = typeof(config) === 'undefined' ? {} : config;
    var movement_mode;
    if (typeof(config.movement_mode) === "undefined") {
        movement_mode = "easeInOut";
    }
    else {
        movement_mode = config.movement_mode;
    }
    var OBJECT_ANIMATION_TIME;
    if (typeof(config.OBJECT_ANIMATION_TIME) === "undefined") {
        OBJECT_ANIMATION_TIME = this.OBJECT_ANIMATION_TIME;
    }
    else {
        OBJECT_ANIMATION_TIME = config.OBJECT_ANIMATION_TIME;
    }
    var get_center = function (obj) {
        if (obj.object_type === 'circle') {
            return [obj.drawn_object.attr('cx'), obj.drawn_object.attr('cy')]
        }
        else if (_.includes(["rect", "wall"], obj.object_type)) {
            var cx = obj.drawn_object.attr('x') + obj.drawn_object.attr('width')/2;
            var cy = obj.drawn_object.attr('y') + obj.drawn_object.attr('height')/2;
            return [cx, cy]
        }
    };

    var calc_magnitude = function (v) {
        return Math.sqrt(v[0]*v[0]+v[1]*v[1]);
    };
    var get_unit_v = function(v) {
        var mag = calc_magnitude(v);
        return _.map(v, function(i) {return i/mag})
    };

    var get_interior_direction = function (obj, unit_v) {
        if (obj.object_type === 'circle') {
            var r = obj.drawn_object.attr('r');
            return _.map(unit_v, function(i) {return i*r})
        }
        else if (_.includes(["rect", "wall"], obj.object_type)) {
            var w = obj.drawn_object.attr('width')*(unit_v[0]/Math.abs(unit_v[0]));
            var h = obj.drawn_object.attr('height')*(unit_v[1]/Math.abs(unit_v[1]));
            var x_indir = [w/2, (w/2)*(unit_v[1]/unit_v[0])];
            var y_indir = [(unit_v[0]/unit_v[1])*(h/2), h/2];
            return _.minBy([x_indir, y_indir], calc_magnitude)
        }
    };

    var obj1 = this.objects[obj1_id];
    var obj2 = this.objects[obj2_id];

    var obj1_c = get_center(obj1);
    var obj2_c = get_center(obj2);

    var obj1_to_obj2 = [obj2_c[0]-obj1_c[0], obj2_c[1]-obj1_c[1]];
    var obj2_to_obj1 = [obj1_c[0]-obj2_c[0], obj1_c[1]-obj2_c[1]];

    var obj1_in_dir = get_interior_direction(obj1, get_unit_v(obj1_to_obj2));
    var obj2_in_dir = get_interior_direction(obj2, get_unit_v(obj2_to_obj1));

    var dobj1 = _.map(_.zip(obj1_to_obj2, obj1_in_dir, obj2_in_dir), function (i) {
        var obj1_to_obj2 = i[0];
        var obj1_in_dir = i[1];
        var obj2_in_dir = i[2];
        return obj1_weight*(obj1_to_obj2 - (obj1_in_dir-obj2_in_dir)*(1-overlap))
    });
    var dobj2 = _.map(_.zip(obj2_to_obj1, obj2_in_dir, obj1_in_dir), function (i) {
        var obj2_to_obj1 = i[0];
        var obj2_in_dir = i[1];
        var obj1_in_dir = i[2];
        return (1-obj1_weight)*(obj2_to_obj1 - (obj2_in_dir-obj1_in_dir)*(1-overlap))
    });

    var move_obj1, move_obj2;
    if (obj1.object_type === 'circle') {
        move_obj1 = Raphael.animation({
            cx : obj1.drawn_object.attr('cx') + dobj1[0],
            cy : obj1.drawn_object.attr('cy') + dobj1[1]
        }, OBJECT_ANIMATION_TIME, movement_mode);
    }
    else if (_.includes(["rect", "wall"], obj1.object_type)) {
        move_obj1 = Raphael.animation({
            x : obj1.drawn_object.attr('x') + dobj1[0],
            y : obj1.drawn_object.attr('y') + dobj1[1]
        }, OBJECT_ANIMATION_TIME, movement_mode);
    }
    obj1.drawn_object.animate(move_obj1);

    if (obj2.object_type === 'circle') {
        move_obj2 = Raphael.animation({
            cx : obj2.drawn_object.attr('cx') + dobj2[0],
            cy : obj2.drawn_object.attr('cy') + dobj2[1]
        }, OBJECT_ANIMATION_TIME, movement_mode);
    }
    else if (_.includes(["rect", "wall"], obj2.object_type)) {
        move_obj2 = Raphael.animation({
            x : obj2.drawn_object.attr('x') + dobj2[0],
            y : obj2.drawn_object.attr('y') + dobj2[1]
        }, OBJECT_ANIMATION_TIME, movement_mode);
    }
    obj2.drawn_object.animate(move_obj2);

    return OBJECT_ANIMATION_TIME
};

GridWorldPainter.prototype.collide_and_return_objs = function
    (obj1_id, obj2_id, obj1_weight, overlap, config) {
    config = typeof(config) === 'undefined' ? {} : config;
    if (typeof(config.movement_mode) === "undefined") {
        movement_mode = "easeInOut";
    }
    else {
        movement_mode = config.movement_mode;
    }
    var OBJECT_ANIMATION_TIME;
    if (typeof(config.OBJECT_ANIMATION_TIME) === "undefined") {
        OBJECT_ANIMATION_TIME = this.OBJECT_ANIMATION_TIME;
    }
    else {
        OBJECT_ANIMATION_TIME = config.OBJECT_ANIMATION_TIME;
    }

    var obj1_orig = this.objects[obj1_id].drawn_object.attr(['x','y','cx','cy']);
    var obj2_orig = this.objects[obj2_id].drawn_object.attr(['x','y','cx','cy']);

    var obj1_reset = Raphael.animation(obj1_orig, OBJECT_ANIMATION_TIME/2, movement_mode);
    var obj2_reset = Raphael.animation(obj2_orig, OBJECT_ANIMATION_TIME/2, movement_mode);

    this.bring_objects_into_contact(obj1_id, obj2_id, obj1_weight, 0, {
        OBJECT_ANIMATION_TIME : OBJECT_ANIMATION_TIME/2
    });
    setTimeout(function(obj1_id, obj2_id, obj1_reset, obj2_reset) {
        this.objects[obj1_id].drawn_object.animate(obj1_reset);
        this.objects[obj2_id].drawn_object.animate(obj2_reset);
    }.bind(this, obj1_id, obj2_id, obj1_reset, obj2_reset),
        OBJECT_ANIMATION_TIME/2);
    return OBJECT_ANIMATION_TIME
}

/*================================================================================================


									Interacting w Objects


================================================================================================*/

GridWorldPainter.prototype.enable_drag_drop = function (object_id, orientation) {
	var painter = this;

	var drag_defer = Q.defer();
	var drop_defer = Q.defer();

	painter.objects[object_id].drawn_object.drag(
		//onmove handler
		$.proxy((function(object_id, orientation) {
				var y_drag_offset;
				switch (orientation) {
					case '^':
						y_drag_offset = 0.02;
						break;
					case 'v':
						y_drag_offset = 0.02;
						break;
					case '<':
						y_drag_offset = 0.1;
						break;
					case '>':
						y_drag_offset = 0.1;
						break;
				}
				return function (dx, dy, px, py, event) {
					//make px, py relative to canvas coordinates
					var offset = $(this.paper.canvas).offset()
					px = px - offset.left;
					py = py - offset.top;

					px = Math.min(Math.max(px, this.TILE_SIZE/2), this.width_px - this.TILE_SIZE/2);
					py = Math.min(Math.max(py, this.TILE_SIZE/2), this.height_px - this.TILE_SIZE/2);

					/*========================================================================
												Dragging a circle
					========================================================================*/
					if (this.objects[object_id].object_type == 'circle') {
						this.objects[object_id].drawn_object.attr({
							cx : px,
							cy : py
						});
					}

					//pixels to grid conversion
					//x = (w - this.DISPLAY_BORDER)/this.TILE_SIZE - .5;
					//y = this.h_to_y((h-d)/t - .5);
					/*========================================================================
												Dragging a rectangle
					========================================================================*/
					if (this.objects[object_id].object_type == 'rect') {
						var object_params = this.objects[object_id].object_params;
						if (_.includes(['^','v'], orientation)) {
							var rect_width = object_params.object_width;
							var rect_length = object_params.object_length;
						}
						else if (_.includes(['<', '>'], orientation)) {
							var rect_width = object_params.object_length;
							var rect_length = object_params.object_width;
						}

						this.objects[object_id].drawn_object.attr({
							x : px-rect_width/2,
							y : py-rect_length/2,
							width : rect_width*painter.TILE_SIZE,
							height : rect_length*painter.TILE_SIZE
						});

						//pixels to grid conversion
						// x = (w-this.DISPLAY_BORDER)/this.TILE_SIZE - .5 + rect_width/2;
						// y = this.h_to_y((h - this.DISPLAY_BORDER)/this.TILE_SIZE -.5+rect_length/2);
					}

					//sprite
					/*========================================================================
												Dragging a sprite
					========================================================================*/
					if (painter.objects[object_id].object_type == 'sprite') {
						var sprite_params = painter.objects[object_id].object_params;
						var s_rowcol = sprite_params.orientation_step_to_row_col(orientation, 1);
						var s_row = s_rowcol[0];
						var s_col = s_rowcol[1];

						var params = {
							x : px - this.TILE_SIZE*(s_col+.5),
							y : py - this.TILE_SIZE*(s_row+.5+y_drag_offset),

							'clip-rect':_.join([
									px-this.TILE_SIZE/2,
									py-this.TILE_SIZE/2,
									painter.TILE_SIZE,
									painter.TILE_SIZE
								], ',')
						}

						painter.objects[object_id].drawn_object.attr(params);
						painter.objects[object_id].object_params.sprite_step = 1;

						//x : (x-s_col)*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.x_adj,
						//y : (painter.y_to_h(y)-s_row)*painter.TILE_SIZE+painter.DISPLAY_BORDER+sprite_params.y_adj,
					}
				}
			})(object_id, orientation), this),

		//onstart handler
		$.proxy((function(object_id, orientation) {
				return function (x, y, event) {
					drag_defer.resolve();

					//orient sprite in a particular way
					if (this.objects[object_id].object_type == 'sprite') {
						this._update_sprite(object_id, {orientation : orientation})
					}
				}

			})(object_id, orientation), this),

		//onend handler
		$.proxy((function(object_id, orientation) {
				return function (event) {
					var offset = $(this.paper.canvas).offset()
					var px = (event.pageX - offset.left);
					var py = (event.pageY - offset.top);

					px = Math.min(Math.max(px, this.TILE_SIZE/2), this.width_px - this.TILE_SIZE/2);
					py = Math.min(Math.max(py, this.TILE_SIZE/2), this.height_px - this.TILE_SIZE/2);
					px -= this.DISPLAY_BORDER;
					py -= this.DISPLAY_BORDER;

					//find closest grid
					var x = Math.round(px/this.TILE_SIZE-.5);
					var y = Math.round(this.h_to_y(py/this.TILE_SIZE-.5));

					this._update_sprite(object_id, {grid_x : x, grid_y : y});

					drop_defer.resolve({
						px : px,
						py : py,
						x : x,
						y : y
					});
				}
			})(object_id, orientation), this)
	)

	return [drag_defer.promise, drop_defer.promise]
}

GridWorldPainter.prototype.disable_drag_drop = function (object_id) {
	if (typeof(object_id) === 'undefined') {
		console.warn("No object_id defined");
	}
	this.objects[object_id].drawn_object.undrag();
}

GridWorldPainter.prototype.enable_on_tile_click = function (handler) {
	//callback will be given context with tile in it
	this.click_handlers = [];
	for (var i = 0; i < this.tiles.length; i++) {
		var bound_handler = handler.bind(this, this.tiles[i])
		this.tiles[i].click(bound_handler);
		this.click_handlers.push(bound_handler);
	}
}

GridWorldPainter.prototype.disable_on_tile_click = function () {
	for (var i = 0; i < this.tiles.length; i++) {
		var bound_handler = this.click_handlers[i];
		this.tiles[i].unclick(bound_handler);
	}
}


/*================================================================================================


										Accessing Objects


================================================================================================*/

GridWorldPainter.prototype.get_object_location = function (object_id) {
	var params = this.objects[object_id].object_params;
	return {x : params.grid_x, y : params.grid_y}
}

/*================================================================================================


							Old functions for backwards compatibility


================================================================================================*/

GridWorldPainter.prototype.draw_agent = function(x, y, agent_id) {
	this.add_object('circle', agent_id, {})
	this.draw_object(x,y,'^',agent_id);
}

GridWorldPainter.prototype.hide_agent = function(agent_id) {
	this.hide_object(agent_id);
}

GridWorldPainter.prototype.show_agent = function(agent_id) {
	this.show_agent(agent_id);
}

GridWorldPainter.prototype.clear_agents = function() {
	this.clear_objects();
}

GridWorldPainter.prototype.animate_agent_movement = function(action, new_x, new_y, agent_id, type) {
	return this.animate_object_movement(action, new_x, new_y, agent_id, type);
}

// module.exports = GridWorldPainter;
