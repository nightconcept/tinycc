const std = @import("std");
const builtin = @import("builtin");
const Io = std.Io;

extern fn tcc_main(argc: c_int, argv: [*c][*c]u8) c_int;

const usage =
    \\MTC (Modern Tiny C Compiler)
    \\Usage:
    \\  mtc file.c [args]            Compile and run
    \\  mtc run file.c -- [args]     Compile and run
    \\  mtc build [tcc arguments]    Build an artifact
    \\  mtc lint file.c              Compile with warnings as errors
    \\  mtc tcc [tcc arguments]      Use the original TCC interface
    \\
;

const archive = @embedFile("mtc-runtime.tar");
const version = std.mem.trim(u8, @embedFile("VERSION"), " \r\n");

pub fn main(init: std.process.Init) u8 {
    return run(init) catch |err| {
        std.debug.print("mtc: {s}\n", .{@errorName(err)});
        return 1;
    };
}

fn run(init: std.process.Init) !u8 {
    const arena = init.arena.allocator();
    const args = try init.minimal.args.toSlice(arena);

    if (args.len == 1 or (args.len == 2 and (eql(args[1], "help") or eql(args[1], "--help") or eql(args[1], "-h")))) {
        var buffer: [1024]u8 = undefined;
        var stdout = Io.File.stdout().writer(init.io, &buffer);
        try stdout.interface.writeAll(usage);
        try stdout.interface.flush();
        return 0;
    }

    const cache = try prepareRuntime(arena, init.io, init.environ_map);
    const routed = try route(arena, cache, args[1..]);
    var argv = try arena.alloc([*c]u8, routed.len + 1);
    argv[0] = @constCast(args[0].ptr);
    for (routed, 1..) |arg, i| argv[i] = @constCast(arg.ptr);
    return @intCast(tcc_main(@intCast(argv.len), argv.ptr));
}

fn route(arena: std.mem.Allocator, cache: []const u8, args: []const [:0]const u8) ![]const [:0]const u8 {
    var out: std.ArrayList([:0]const u8) = .empty;
    try out.append(arena, try std.fmt.allocPrintSentinel(arena, "-B{s}", .{cache}, 0));

    if (eql(args[0], "tcc") or eql(args[0], "build")) {
        try out.appendSlice(arena, args[1..]);
    } else if (eql(args[0], "lint")) {
        try out.appendSlice(arena, &.{ "-Wall", "-Werror", "-c", "-o", if (builtin.os.tag == .windows) "NUL" else "/dev/null" });
        try out.appendSlice(arena, args[1..]);
    } else {
        const start: usize = if (eql(args[0], "run")) 1 else 0;
        var delimiter = true;
        try out.append(arena, "-run");
        for (args[start..]) |arg| {
            if (delimiter and eql(arg, "--")) {
                delimiter = false;
                continue;
            }
            try out.append(arena, arg);
        }
    }
    return out.toOwnedSlice(arena);
}

fn prepareRuntime(arena: std.mem.Allocator, io: Io, env: *const std.process.Environ.Map) ![]const u8 {
    const cache = if (env.get("MTC_CACHE_DIR")) |path|
        path
    else blk: {
        const base = switch (builtin.os.tag) {
            .windows => env.get("LOCALAPPDATA") orelse return error.MissingCacheDirectory,
            .macos => try std.fs.path.join(arena, &.{ env.get("HOME") orelse return error.MissingCacheDirectory, "Library", "Caches" }),
            else => env.get("XDG_CACHE_HOME") orelse try std.fs.path.join(arena, &.{ env.get("HOME") orelse return error.MissingCacheDirectory, ".cache" }),
        };
        const target = try std.fmt.allocPrint(arena, "{s}-{s}-{s}", .{ version, @tagName(builtin.cpu.arch), @tagName(builtin.os.tag) });
        break :blk try std.fs.path.join(arena, &.{ base, "mtc", target });
    };

    const marker = try std.fs.path.join(arena, &.{ cache, ".complete" });
    Io.Dir.access(.cwd(), io, marker, .{}) catch |err| switch (err) {
        error.FileNotFound => {
            try Io.Dir.createDirPath(.cwd(), io, cache);
            var dir = try Io.Dir.openDir(.cwd(), io, cache, .{});
            defer dir.close(io);
            var reader: Io.Reader = .fixed(archive);
            // ponytail: concurrent first runs may race; add a cache lock if this is observed in practice.
            try std.tar.extract(io, dir, &reader, .{});
            try dir.writeFile(io, .{ .sub_path = ".complete", .data = version });
        },
        else => return err,
    };
    return cache;
}

fn eql(a: []const u8, b: []const u8) bool {
    return std.mem.eql(u8, a, b);
}

test "routes commands" {
    var arena_state = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena_state.deinit();
    const arena = arena_state.allocator();

    const shorthand = try route(arena, "/cache", &.{"hello.c"});
    try std.testing.expectEqualStrings("-B/cache", shorthand[0]);
    try std.testing.expectEqualStrings("-run", shorthand[1]);
    try std.testing.expectEqualStrings("hello.c", shorthand[2]);

    const build = try route(arena, "/cache", &.{ "build", "hello.c", "-o", "hello" });
    try std.testing.expectEqualStrings("hello.c", build[1]);
    try std.testing.expectEqualStrings("-o", build[2]);

    const run_args = try route(arena, "/cache", &.{ "run", "hello.c", "--", "one" });
    try std.testing.expectEqualStrings("hello.c", run_args[2]);
    try std.testing.expectEqualStrings("one", run_args[3]);
}
