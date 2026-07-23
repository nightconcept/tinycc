const std = @import("std");
const builtin = @import("builtin");
const Io = std.Io;

extern fn tcc_main(argc: c_int, argv: [*c][*c]u8) c_int;

const archive = @embedFile("build/ztcc-runtime.tar");
const version = std.mem.trim(u8, @embedFile("src/VERSION"), " \r\n");

pub fn main(init: std.process.Init) u8 {
    return run(init) catch |err| {
        std.debug.print("ztcc: {s}\n", .{@errorName(err)});
        return 1;
    };
}

fn run(init: std.process.Init) !u8 {
    const arena = init.arena.allocator();
    const args = try init.minimal.args.toSlice(arena);

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
    try out.appendSlice(arena, args);
    return out.toOwnedSlice(arena);
}

fn prepareRuntime(arena: std.mem.Allocator, io: Io, env: *const std.process.Environ.Map) ![]const u8 {
    const cache = if (env.get("ZTCC_CACHE_DIR")) |path|
        path
    else blk: {
        const base = switch (builtin.os.tag) {
            .windows => env.get("LOCALAPPDATA") orelse return error.MissingCacheDirectory,
            .macos => try std.fs.path.join(arena, &.{ env.get("HOME") orelse return error.MissingCacheDirectory, "Library", "Caches" }),
            else => env.get("XDG_CACHE_HOME") orelse try std.fs.path.join(arena, &.{ env.get("HOME") orelse return error.MissingCacheDirectory, ".cache" }),
        };
        const target = try std.fmt.allocPrint(arena, "{s}-{s}-{s}", .{ version, @tagName(builtin.cpu.arch), @tagName(builtin.os.tag) });
        break :blk try std.fs.path.join(arena, &.{ base, "ztcc", target });
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

test "routes commands" {
    var arena_state = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena_state.deinit();
    const arena = arena_state.allocator();

    const routed = try route(arena, "/cache", &.{ "-run", "hello.c", "-o", "hello" });
    try std.testing.expectEqualStrings("-B/cache", routed[0]);
    try std.testing.expectEqualStrings("-run", routed[1]);
    try std.testing.expectEqualStrings("hello.c", routed[2]);
    try std.testing.expectEqualStrings("-o", routed[3]);
    try std.testing.expectEqualStrings("hello", routed[4]);
}
