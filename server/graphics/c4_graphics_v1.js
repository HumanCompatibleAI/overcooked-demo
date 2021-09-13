// Global variable to indicate whether graphics context is finished initialized
// Since it only ever gets set once, we don't have to worry about race conditions
var initialized = false;

var array_equals = function(arr1, arr2) {
    if (arr1.length !== arr2.length) {
        return false;
    }
    for (i = 0; i < arr1.length; i++) {
        if (arr1[i] !== arr2[i]) {
            return false;
        }
    }
    return true;
}

window.kaggle = {
    "debug": false,
    "playing": true,
    "step": 0,
    "controls": false,
    "environment": {
      "id": "27e36f1a-11c6-11ec-b1e7-faffc24beb6c",
      "name": "connectx",
      "title": "ConnectX",
      "description": "Classic Connect in a row but configurable.",
      "version": "1.0.1",
      "configuration": {
        "episodeSteps": 1000,
        "actTimeout": 2,
        "runTimeout": 1200,
        "columns": 7,
        "rows": 6,
        "inarow": 4,
        "agentTimeout": 60,
        "timeout": 2
      },
      "specification": {
        "action": {
          "description": "Column to drop a checker onto the board.",
          "type": "integer",
          "minimum": 0,
          "default": 0
        },
        "agents": [
          2
        ],
        "configuration": {
          "episodeSteps": {
            "description": "Maximum number of steps in the episode.",
            "type": "integer",
            "minimum": 1,
            "default": 1000
          },
          "actTimeout": {
            "description": "Maximum runtime (seconds) to obtain an action from an agent.",
            "type": "number",
            "minimum": 0,
            "default": 2
          },
          "runTimeout": {
            "description": "Maximum runtime (seconds) of an episode (not necessarily DONE).",
            "type": "number",
            "minimum": 0,
            "default": 1200
          },
          "columns": {
            "description": "The number of columns on the board",
            "type": "integer",
            "default": 7,
            "minimum": 1
          },
          "rows": {
            "description": "The number of rows on the board",
            "type": "integer",
            "default": 6,
            "minimum": 1
          },
          "inarow": {
            "description": "The number of checkers in a row required to win.",
            "type": "integer",
            "default": 4,
            "minimum": 1
          },
          "agentTimeout": {
            "description": "Obsolete field kept for backwards compatibility, please use observation.remainingOverageTime.",
            "type": "number",
            "minimum": 0,
            "default": 60
          },
          "timeout": {
            "description": "Obsolete copy of actTimeout maintained for backwards compatibility. May be removed in the future.",
            "type": "integer",
            "default": 2,
            "minimum": 0
          }
        },
        "info": {},
        "observation": {
          "remainingOverageTime": {
            "description": "Total remaining banked time (seconds) that can be used in excess of per-step actTimeouts -- agent is disqualified with TIMEOUT status when this drops below 0.",
            "shared": false,
            "type": "number",
            "minimum": 0,
            "default": 60
          },
          "step": {
            "description": "Current step within the episode.",
            "type": "integer",
            "shared": true,
            "minimum": 0,
            "default": 0
          },
          "board": {
            "description": "Serialized grid (rows x columns). 0 = Empty, 1 = P1, 2 = P2",
            "type": "array",
            "shared": true,
            "default": []
          },
          "mark": {
            "defaults": [
              1,
              2
            ],
            "description": "Which checkers are the agents.",
            "enum": [
              1,
              2
            ]
          }
        },
        "reward": {
          "description": "-1 = Lost, 0 = Draw/Ongoing, 1 = Won",
          "enum": [
            -1,
            0,
            1
          ],
          "default": 0,
          "type": [
            "number",
            "null"
          ]
        }
      },
      "steps": [
        [
          {
            "action": 0,
            "reward": 0,
            "info": {},
            "observation": {
              "remainingOverageTime": 60,
              "step": 0,
              "board": [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0
              ],
              "mark": 1
            },
            "status": "ACTIVE"
          },
          {
            "action": 0,
            "reward": 0,
            "info": {},
            "observation": {
              "remainingOverageTime": 60,
              "mark": 2
            },
            "status": "INACTIVE"
          }
        ],
        [
          {
            "action": 0,
            "reward": 0,
            "info": {},
            "observation": {
              "remainingOverageTime": 60,
              "step": 0,
              "board": [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0
              ],
              "mark": 1
            },
            "status": "ACTIVE"
          },
          {
            "action": 0,
            "reward": 0,
            "info": {},
            "observation": {
              "remainingOverageTime": 60,
              "mark": 2
            },
            "status": "INACTIVE"
          }
        ]
      ],
      "rewards": [
        0,
        0
      ],
      "statuses": [
        "ACTIVE",
        "INACTIVE"
      ],
      "schema_version": 1,
      "info": {}
    },
    "logs": [
      []
    ],
    "mode": "html"
  };
  
  
  window.kaggle.renderer =
function renderer({
    act,
    agents,
    environment,
    frame,
    height = 400,
    interactive,
    isInteractive,
    parent,
    step,
    update,
    width = 400,
    }) {
    // Configuration.
    const { rows, columns, inarow } = environment.configuration;
  
    // Common Dimensions.
    const unit = 8;
    const minCanvasSize = Math.min(height, width);
    const minOffset = minCanvasSize > 400 ? 30 : unit / 2;
    const cellSize = Math.min(
      (width - minOffset * 2) / columns,
      (height - minOffset * 2) / rows
    );
    const cellInset = 0.8;
    const pieceScale = cellSize / 100;
    const xOffset = Math.max(0, (width - cellSize * columns) / 2);
    const yOffset = Math.max(0, (height - cellSize * rows) / 2);
  
    // Canvas Setup.
    let canvas = parent.querySelector("canvas");
    if (!canvas) {
      canvas = document.createElement("canvas");
      parent.appendChild(canvas);
  
      if (interactive) {
        canvas.addEventListener("click", evt => {
          if (!isInteractive()) return;
          const rect = evt.target.getBoundingClientRect();
          const col = Math.floor((evt.clientX - rect.left - xOffset) / cellSize);
          if (col >= 0 && col < columns) act(col);
        });
      }
    }
    canvas.style.cursor = isInteractive() ? "pointer" : "default";
  
    // Character Paths (based on 100x100 tiles).
    const kPath = new Path2D(
      `M78.3,96.5c-0.1,0.4-0.5,0.6-1.1,0.6H64.9c-0.7,0-1.4-0.3-1.9-1l-20.3-26L37,75.5v20.1 c0,0.9-0.5,1.4-1.4,1.4H26c-0.9,0-1.4-0.5-1.4-1.4V3.9c0-0.9,0.5-1.4,1.4-1.4h9.5C36.5,2.5,37,3,37,3.9v56.5l24.3-24.7 c0.6-0.6,1.3-1,1.9-1H76c0.6,0,0.9,0.2,1.1,0.7c0.2,0.6,0.1,1-0.1,1.2l-25.7,25L78,95.1C78.4,95.5,78.5,95.9,78.3,96.5z`
    );
    const goose1Path = new Path2D(
      `M8.8,92.7c-4-18.5,4.7-37.2,20.7-46.2c0,0,2.7-1.4,3.4-1.9c2.2-1.6,3-2.1,3-5c0-5-2.1-7.2-2.1-7.2 c-3.9-3.3-6.3-8.2-6.3-13.7c0-10,8.1-18.1,18.1-18.1s18.1,8.1,18.1,18.1c0,6-1.5,32.7-2.3,38.8l-0.1,1`
    );
    const goose2Path = new Path2D(
      `M27.4,19L8.2,27.6c0,0-7.3,2.9,2.6,5c6.1,1.3,24,5.9,24,5.9l1,0.3`
    );
    const goose3Path = new Path2D(
      `M63.7,99.6C52.3,99.6,43,90.3,43,78.9s9.3-20.7,20.7-20.7c10.6,0,34.4,0.1,35.8,9`
    );
  
    // Canvas setup and reset.
    let c = canvas.getContext("2d");
    canvas.width = width;
    canvas.height = height;
    c.fillStyle = "#000B2A";
    c.fillRect(0, 0, canvas.width, canvas.height);
  
    const getRowCol = cell => [Math.floor(cell / columns), cell % columns];
  
    const getColor = (mark, opacity = 1) => {
      if (mark === 1) return `rgba(0,255,255,${opacity})`;
      if (mark === 2) return `rgba(255,255,255,${opacity})`;
      return "#fff";
    };
  
    const drawCellCircle = (cell, xFrame = 1, yFrame = 1, radiusOffset = 0) => {
      const [row, col] = getRowCol(cell);
      c.arc(
        xOffset + xFrame * (col * cellSize + cellSize / 2),
        yOffset + yFrame * (row * cellSize + cellSize / 2),
        (cellInset * cellSize) / 2 - radiusOffset,
        2 * Math.PI,
        false
      );
    };
  
    // Render the pieces.
    const board = environment.steps[step][0].observation.board;
  
    const drawPiece = mark => {
      // Base Styles.
      const opacity = minCanvasSize < 300 ? 0.6 - minCanvasSize / 1000 : 0.1;
      c.fillStyle = getColor(mark, opacity);
      c.strokeStyle = getColor(mark);
      c.shadowColor = getColor(mark);
      c.shadowBlur = 8 / cellInset;
      c.lineWidth = 1 / cellInset;
  
      // Outer circle.
      c.save();
      c.beginPath();
      c.arc(50, 50, 50, 2 * Math.PI, false);
      c.closePath();
      c.lineWidth *= 4;
      c.stroke();
      c.fill();
      c.restore();
  
      // Inner circle.
      c.beginPath();
      c.arc(50, 50, 40, 2 * Math.PI, false);
      c.closePath();
      c.stroke();
  
      // Kaggle "K".
      if (mark === 1) {
        const scale = 0.54;
        c.save();
        c.translate(23, 23);
        c.scale(scale, scale);
        c.lineWidth /= scale;
        c.shadowBlur /= scale;
        c.stroke(kPath);
        c.restore();
      }
  
      // Kaggle "Goose".
      if (mark === 2) {
        const scale = 0.6;
        c.save();
        c.translate(24, 28);
        c.scale(scale, scale);
        c.lineWidth /= scale;
        c.shadowBlur /= scale;
        c.stroke(goose1Path);
        c.stroke(goose2Path);
        c.stroke(goose3Path);
        c.beginPath();
        c.arc(38.5, 18.6, 2.7, 0, Math.PI * 2, false);
        c.closePath();
        c.fill();
        c.restore();
      }
    };
  
    for (let i = 0; i < board.length; i++) {
      const [row, col] = getRowCol(i);
      if (board[i] === 0) continue;
      // Easing In.
      let yFrame = Math.min(
        (columns * Math.pow(frame, 3)) / Math.floor(i / columns),
        1
      );
  
      if (
        step > 0 &&
        environment.steps[step - 1][0].observation.board[i] === board[i]
      ) {
        yFrame = 1;
      }
  
      c.save();
      c.translate(
        xOffset + cellSize * col + (cellSize - cellSize * cellInset) / 2,
        yOffset +
          yFrame * (cellSize * row) +
          (cellSize - cellSize * cellInset) / 2
      );
      c.scale(pieceScale * cellInset, pieceScale * cellInset);
      drawPiece(board[i]);
      c.restore();
    }
  
    // Background Gradient.
    const bgRadius = (Math.min(rows, columns) * cellSize) / 2;
    const bgStyle = c.createRadialGradient(
      xOffset + (cellSize * columns) / 2,
      yOffset + (cellSize * rows) / 2,
      0,
      xOffset + (cellSize * columns) / 2,
      yOffset + (cellSize * rows) / 2,
      bgRadius
    );
    bgStyle.addColorStop(0, "#000B49");
    bgStyle.addColorStop(1, "#000B2A");
  
    // Render the board overlay.
    c.beginPath();
    c.rect(0, 0, canvas.width, canvas.height);
    c.closePath();
    c.shadowBlur = 0;
    for (let i = 0; i < board.length; i++) {
      drawCellCircle(i);
      c.closePath();
    }
    c.fillStyle = bgStyle;
    c.fill("evenodd");
  
    // Render the board overlay cell outlines.
    for (let i = 0; i < board.length; i++) {
      c.beginPath();
      drawCellCircle(i);
      c.strokeStyle = "#0361B2";
      c.lineWidth = 1;
      c.stroke();
      c.closePath();
    }
  
    const drawLine = (fromCell, toCell) => {
      if (frame < 0.5) return;
      const lineFrame = (frame - 0.5) / 0.5;
      const x1 = xOffset + (fromCell % columns) * cellSize + cellSize / 2;
      const x2 =
        x1 +
        lineFrame *
          (xOffset + ((toCell % columns) * cellSize + cellSize / 2) - x1);
      const y1 =
        yOffset + Math.floor(fromCell / columns) * cellSize + cellSize / 2;
      const y2 =
        y1 +
        lineFrame *
          (yOffset + Math.floor(toCell / columns) * cellSize + cellSize / 2 - y1);
      c.beginPath();
      c.lineCap = "round";
      c.lineWidth = 4;
      c.strokeStyle = getColor(board[fromCell]);
      c.shadowBlur = 8;
      c.shadowColor = getColor(board[fromCell]);
      c.moveTo(x1, y1);
      c.lineTo(x2, y2);
      c.stroke();
    };
  
    // Generate a graph of the board.
    const getCell = (cell, rowOffset, columnOffset) => {
      const row = Math.floor(cell / columns) + rowOffset;
      const col = (cell % columns) + columnOffset;
      if (row < 0 || row >= rows || col < 0 || col >= columns) return -1;
      return col + row * columns;
    };
    const makeNode = cell => {
      const node = { cell, directions: [], value: board[cell] };
      for (let r = -1; r <= 1; r++) {
        for (let c = -1; c <= 1; c++) {
          if (r === 0 && c === 0) continue;
          node.directions.push(getCell(cell, r, c));
        }
      }
      return node;
    };
    const graph = board.map((_, i) => makeNode(i));
  
    // Check for any wins!
    const getSequence = (node, direction) => {
      const sequence = [node.cell];
      while (sequence.length < inarow) {
        const next = graph[node.directions[direction]];
        if (!next || node.value !== next.value || next.value === 0) return;
        node = next;
        sequence.push(node.cell);
      }
      return sequence;
    };
  
    // Check all nodes.
    for (let i = 0; i < board.length; i++) {
      // Check all directions (not the most efficient).
      for (let d = 0; d < 8; d++) {
        const seq = getSequence(graph[i], d);
        if (seq) {
          drawLine(seq[0], seq[inarow - 1]);
          i = board.length;
          break;
        }
      }
    }

    // Label the columns with the numbers needed for user input
    for (let col = 0; col < columns; col++) {
        let x = xOffset + cellSize * col + cellSize / 2 - (cellSize * (1-cellInset)) / 2;
        let y = yOffset;
        c.font = "40px Serif";
        c.strokeStyle = "white";
        c.strokeText(col+1, x, y);
    }
  };
const h = htm.bind(preact.h);
const { useContext, useEffect, useRef, useState } = preactHooks;
const styled = window.styled.default;

const Context = preact.createContext({ flag : false });

const Loading = styled.div`
    animation: rotate360 1.1s infinite linear;
    border: 8px solid rgba(255, 255, 255, 0.2);
    border-left-color: #0cb1ed;
    border-radius: 50%;
    height: 40px;
    position: relative;
    transform: translateZ(0);
    width: 40px;

    @keyframes rotate360 {
    0% {
        transform: rotate(0deg);
    }
    100% {
        transform: rotate(360deg);
    }
    }
`;

const Renderer = styled((props) => {
    const context = useContext(Context);
    const { animate, debug, playing, renderer, speed } = context;
    const ref = preact.createRef();

    useEffect(async () => {
    if (!ref.current) return;

    const renderFrame = async (start, step, lastFrame) => {
        if (step !== context.step) return;
        if (lastFrame === 1) {
        if (!animate) return;
        start = Date.now();
        }
        const frame =
        playing || animate
            ? Math.min((Date.now() - start) / speed, 1)
            : 1;
        try {
        await renderer({
            ...context,
            frame,
            height: ref.current.clientHeight,
            hooks: preactHooks,
            parent: ref.current,
            preact,
            styled,
            width: ref.current.clientWidth,
        });
        } catch (error) {
        if (debug) console.error(error);
        console.log({ ...context, frame, error });
        } finally {
        if (debug) console.timeEnd("render");
        }
        window.requestAnimationFrame(() => renderFrame(start, step, frame));
    };

    await renderFrame(Date.now(), context.step);
    }, [ref.current, context.step, context.renderer, context.flag]);

    return h`<div className=${props.className} ref=${ref} />`;
})`
    align-items: center;
    box-sizing: border-box;
    display: flex;
    height: 100%;
    left: 0;
    justify-content: center;
    position: absolute;
    top: 0;
    width: 100%;
`;

const Processing = styled((props) => {
    const { processing } = useContext(Context);
    const text = processing === true ? "Processing..." : processing;
    return h`<div className=${props.className}>${text}</div>`;
})`
    bottom: 0;
    color: #fff;
    font-size: 12px;
    left: 0;
    line-height: 24px;
    position: absolute;
    text-align: center;
    width: 100%;
`;

const Viewer = styled((props) => {
    const { processing } = useContext(Context);
    return h`<div className=${props.className}>
    <${Renderer} />
    ${processing && h`<${Processing} />`}
    </div>`;
})`
    background-color: #000b2a;
    background-image: radial-gradient(
    circle closest-side,
    #000b49,
    #000b2a
    );
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
    width: 100%;
`;

const Player = styled((props) => {
    const context = useContext(Context);
    const { loading, width } = context;
    return h`
    <div className=${props.className}>
        ${loading && h`<${Loading} />`}
        ${!loading && h`<${Viewer} />`}
    </div>`;
})`
    align-items: center;
    background: #212121;
    border: 4px solid #212121;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    height: 100%;
    justify-content: center;
    position: relative;
    width: 100%;
`;
  
const App = () => {
    const renderCountRef = useRef(0);
    const [_, setRenderCount] = useState(0);

    // These are bindings to the 0-9 keys and are milliseconds of timeout per step
    const speeds = [
    0,
    3000,
    1000,
    500,
    333, // Default
    200,
    100,
    50,
    25,
    10,
    ];

    const contextRef = useRef({
    animate: false,
    agents: [],
    flag: false,
    controls: false,
    debug: false,
    environment: { steps: [], info: {} },
    header: window.innerHeight >= 600,
    height: window.innerHeight,
    interactive: false,
    legend: true,
    loading: false,
    playing: false,
    processing: false,
    renderer: () => "DNE",
    settings: false,
    speed: speeds[4],
    step: 0,
    width: window.innerWidth,
    });

    // Context helpers.
    const rerender = (contextRef.current.rerender = () =>
    setRenderCount((renderCountRef.current += 1)));
    const setStep = (contextRef.current.setStep = (newStep) => {
    contextRef.current.step = newStep;
    rerender();
    });
    const setFlag = (contextRef.current.setFlag = () => {
    contextRef.current.flag = !contextRef.current.flag;
    rerender();
    });
    const setPlaying = (contextRef.current.setPlaying = (playing) => {
    contextRef.current.playing = playing;
    rerender();
    });
    const pause = (contextRef.current.pause = () => setPlaying(false));

    const playNext = () => {
    const context = contextRef.current;

    if (
        context.playing &&
        context.step < context.environment.steps.length - 1
    ) {
        setStep(context.step + 1);
        play(true);
    } else {
        pause();
    }
    };

    const play = (contextRef.current.play = (continuing) => {
    const context = contextRef.current;
    if (context.playing && !continuing) return;
    if (!context.playing) setPlaying(true);
    if (
        !continuing &&
        context.step === context.environment.steps.length - 1
    ) {
        setStep(0);
    }
    setTimeout(playNext, context.speed);
    });

    const updateContext = (o) => {
    const context = contextRef.current;
    Object.assign(context, o, {
        environment: { ...context.environment, ...(o.environment || {}) },
    });
    rerender();
    };

    const updateState = (state) => {
        let new_board = state.board

        const context = contextRef.current;
        let steps = context.environment.steps;
        let last_step = steps[steps.length-1];
        let last_board = last_step[0].observation.board;

        if (array_equals(new_board, last_board)) {
            // Board unchanged, no update needed
            return;
        }

        // Update the board state
        let new_step = JSON.parse(JSON.stringify(last_step));
        new_step[0].observation.board = new_board;
        new_step[1].observation.board = new_board;
        steps.push(new_step);
        steps.shift();

        // Set the flag to tell renderer it's time to re-render
        setFlag();
        setPlaying(true);
    }
    window.updateState = updateState;

    // First time setup.
    useEffect(() => {
    // Timeout is used to ensure useEffect renders once.
    setTimeout(() => {
        // Initialize context with window.kaggle.
        updateContext(window.kaggle || {});

        if (window.kaggle.playing) {
            play(true);
        }
        initialized = true;
    }, 1);
    }, []);

    // Ability to update context.
    contextRef.current.update = updateContext;
    window.update = updateContext;

    // Ability to communicate with ipython.
    // const execute = (contextRef.current.execute = (source) =>
    // new Promise((resolve, reject) => {
    //     try {
    //     window.parent.IPython.notebook.kernel.execute(source, {
    //         iopub: {
    //         output: (resp) => {
    //             const type = resp.msg_type;
    //             if (type === "stream") return resolve(resp.content.text);
    //             if (type === "error") return reject(new Error(resp.evalue));
    //             return reject(new Error("Unknown message type: " + type));
    //         },
    //         },
    //     });
    //     } catch (e) {
    //     reject(new Error("IPython Unavailable: " + e));
    //     }
    // }));

    // const dummy_execute = (contextRef.current.execute = (source) =>
    // new Promise((resolve, reject) => {
    //     let new_steps = JSON.parse(JSON.stringify(window.kaggle.environment.steps));
    //     let new_step = JSON.parse(JSON.stringify(new_steps[0]));
    //     let new_board = JSON.parse(JSON.stringify(new_step[0].observation.board))
    //     new_board[1] = 1;
    //     new_step[0].observation.board = new_board;
    //     new_step[1].observation.board = new_board;
    //     new_steps.push(new_step);
    //     console.log(new_steps);
    //     return resolve(new_steps);
    // }));

    // Ability to return an action from an interactive session.
    // contextRef.current.act = (action) => {
    // const id = contextRef.current.environment.id;
    // updateContext({ processing: true });
    // dummy_execute()
    //     .then((resp) => {
    //     console.log("resolved!")
    //     try {
    //         updateContext({
    //         processing: false,
    //         environment: { steps: resp },
    //         });
    //         console.log("Updated!")
    //         play();
    //     } catch (e) {
    //         updateContext({ processing: resp.split("\n")[0] });
    //         console.error(resp, e);
    //     }
    //     })
    //     .catch((e) => console.error(e));
    // };
    // window.act = contextRef.current.act;

    // Check if currently interactive.
    contextRef.current.isInteractive = () => {
        return false;
    };

    return h`
    <${Context.Provider} value=${contextRef.current}>
        <${Player} />
    <//>`;
};


var container_id;
const noop = () => {};

function drawState(state) {
    if (initialized) {
        window.updateState(state);
    }
};

function graphics_start(config) {
    container_id = config.container_id;
    preact.render(h`<${App} />`, document.body, $(`#${container_id}`));
};

function graphics_end() {
    noop();
}

// Testing purposes only
var current = 2;
var current_board = window.kaggle.environment.steps[1][0].observation.board;
function drop(i) {
  let new_state = {};
  current = current == 1 ? 2 : 1;
  new_board = JSON.parse(JSON.stringify(current_board));
  let idx = 41 - (6 - i);
  while (new_board[idx] != 0 && idx > 0) {
      idx -= 7;
  }
  new_board[idx] = current;
  new_state.board = new_board;
  window.updateState(new_state);
  current_board = new_board;
}